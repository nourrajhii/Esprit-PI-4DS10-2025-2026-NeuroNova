'use client'
import { useState, useEffect, useCallback, useRef } from 'react'
import SubscriptionGuard from '@/components/SubscriptionGuard'
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ForecastPoint { date: string; prix_predit: number; ic_bas: number | null; ic_haut: number | null }
interface HorizonData   { valeur: number; variation_pct: number }
interface AgentResponse {
  mode: 'vente' | 'location'
  gouvernorat: string; ville: string; quartier: string; standing: string
  type_bien: string | null; composition: string | null; superficie: number | null
  valeur_saisie: number; valeur_totale_actuelle: number | null
  prix_base: number; prix_reference_ajuste: number; prix_moyen_marche: number
  diff_vs_marche_pct: number; statut_prix: string
  coeff_standing: number; score_attributs: number; score_proximite: number
  attributs_actifs: Record<string, number>; services_detectes: Record<string, number>
  taux_mensuel: number; taux_annuel: number
  horizons: { '6': HorizonData; '12': HorizonData; '18': HorizonData; '24': HorizonData }
  tendance: 'hausse' | 'baisse' | 'stable'
  risque: 'Faible' | 'Modéré' | 'Élevé'
  tension: string; analyse_marche: string; facteurs: string[]; recommandation: string
  points: ForecastPoint[]; lat: number | null; lng: number | null
}

// ── Static data ───────────────────────────────────────────────────────────────

const GOUVERNORATS = [
  'Tunis','Ariana','Ben Arous','Manouba','Nabeul','Zaghouan','Bizerte',
  'Béja','Jendouba','Kef','Siliana','Sousse','Monastir','Mahdia','Sfax',
  'Kairouan','Kasserine','Sidi Bouzid','Gabès','Medenine','Tataouine',
  'Gafsa','Tozeur','Kébili',
]
const TYPES_BIEN  = ['appartement','villa','maison','terrain','bureau']
const COMPS       = ['S+1','S+2','S+3','S+4']
const STANDINGS: { value: string; label: string; desc: string; color: string }[] = [
  { value:'populaire',     label:'Populaire',     desc:'×0.75', color:'bg-slate-100 border-slate-300 text-slate-600'   },
  { value:'intermédiaire', label:'Intermédiaire', desc:'×1.00', color:'bg-blue-50 border-blue-300 text-blue-700'       },
  { value:'résidentiel',   label:'Résidentiel',   desc:'×1.30', color:'bg-violet-50 border-violet-300 text-violet-700' },
  { value:'luxe',          label:'Luxe',          desc:'×1.70', color:'bg-amber-50 border-amber-300 text-amber-700'    },
  { value:'vue_mer',       label:'Vue mer',       desc:'×1.50', color:'bg-cyan-50 border-cyan-300 text-cyan-700'       },
]
const ATTRS_VENTE = [
  { key:'garage',    label:'Garage / Parking',  pct:'+6%'  },
  { key:'piscine',   label:'Piscine',            pct:'+10%' },
  { key:'sous_sol',  label:'Sous-sol',           pct:'+5%'  },
  { key:'terrasse',  label:'Terrasse',           pct:'+7%'  },
  { key:'ascenseur', label:'Ascenseur',          pct:'+4%'  },
  { key:'vue_mer',   label:'Vue mer',            pct:'+18%' },
  { key:'jardin',    label:'Jardin privatif',    pct:'+8%'  },
]
const ATTRS_LOC = [
  { key:'garage',      label:'Garage / Parking',      pct:'+8%'  },
  { key:'piscine',     label:'Piscine',                pct:'+12%' },
  { key:'ascenseur',   label:'Ascenseur',              pct:'+5%'  },
  { key:'terrasse',    label:'Terrasse / Balcon',      pct:'+6%'  },
  { key:'meuble',      label:'Meublé',                 pct:'+15%' },
  { key:'clim',        label:'Climatisation incluse',  pct:'+7%'  },
  { key:'gardiennage', label:'Gardiennage / Sécurité', pct:'+5%'  },
  { key:'vue_mer',     label:'Vue mer / Vue dégagée',  pct:'+20%' },
]
const SERVICE_CFG: Record<string,{label:string;color:string;coeff:number}> = {
  supermarche: { label:'Supermarché / Épicerie',  color:'#10b981', coeff:3 },
  pharmacie:   { label:'Pharmacie',               color:'#3b82f6', coeff:2 },
  ecole:       { label:'École / Lycée',           color:'#8b5cf6', coeff:4 },
  transport:   { label:'Transport en commun',     color:'#f59e0b', coeff:5 },
  restaurant:  { label:'Café / Restaurant',       color:'#ec4899', coeff:1 },
  hopital:     { label:'Hôpital / Clinique',      color:'#ef4444', coeff:3 },
  mosquee:     { label:'Mosquée',                 color:'#6366f1', coeff:1 },
  parc:        { label:'Parc / Espace vert',      color:'#22c55e', coeff:3 },
}
const ATTR_LABELS: Record<string,string> = {
  garage:'Garage', piscine:'Piscine', sous_sol:'Sous-sol', terrasse:'Terrasse',
  ascenseur:'Ascenseur', vue_mer:'Vue mer', jardin:'Jardin', meuble:'Meublé',
  clim:'Climatisation', gardiennage:'Gardiennage',
}
const BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000'
const FMT  = new Intl.NumberFormat('fr-TN', { maximumFractionDigits: 0 })
const FMT2 = new Intl.NumberFormat('fr-TN', { maximumFractionDigits: 1 })

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('fr-FR', { month:'short', year:'2-digit' })
}

// ── Overpass node classifier ──────────────────────────────────────────────────
function classifyNode(tags: Record<string,string>): string | null {
  const { amenity, shop, highway, railway, leisure, religion } = tags
  if (shop && ['supermarket','convenience','grocery','bakery'].includes(shop)) return 'supermarche'
  if (amenity === 'pharmacy' || amenity === 'chemist') return 'pharmacie'
  if (amenity && ['school','college','university','kindergarten'].includes(amenity)) return 'ecole'
  if (highway === 'bus_stop' || (railway && ['station','halt','tram_stop','subway_entrance'].includes(railway))) return 'transport'
  if (amenity && ['restaurant','cafe','fast_food','bar'].includes(amenity)) return 'restaurant'
  if (amenity && ['hospital','clinic','doctors','dentist'].includes(amenity)) return 'hopital'
  if (amenity === 'place_of_worship' && religion === 'muslim') return 'mosquee'
  if (leisure && ['park','garden','playground'].includes(leisure)) return 'parc'
  return null
}

// ── ProximityMap sub-component ────────────────────────────────────────────────
function ProximityMap({ lat, lng, ville, onServices }: {
  lat: number; lng: number; ville: string
  onServices: (s: string[]) => void
}) {
  const divRef  = useRef<HTMLDivElement>(null)
  const mapRef  = useRef<unknown>(null)
  const [detected, setDetected]   = useState<{type:string;name:string}[]>([])
  const [loadingMap, setLoadingMap] = useState(false)
  const [mapError, setMapError]   = useState<string|null>(null)
  const [score, setScore]         = useState(0)

  // Init Leaflet once
  useEffect(() => {
    if (!divRef.current || mapRef.current) return
    // Guard against React Strict Mode double-invoke: check if Leaflet already owns this div
    const div = divRef.current as HTMLDivElement & { _leaflet_id?: number }
    if (div._leaflet_id) return
    import('leaflet').then(L => {
      // Re-check after async gap — component may have unmounted
      if (!divRef.current || mapRef.current) return
      if ((divRef.current as HTMLDivElement & { _leaflet_id?: number })._leaflet_id) return
      delete (L.Icon.Default.prototype as unknown as Record<string,unknown>)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      })
      const map = (L as typeof L).map(divRef.current!, { zoomControl:true, scrollWheelZoom:false })
      ;(L as typeof L).tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:'© OpenStreetMap', maxZoom:18,
      }).addTo(map as Parameters<typeof L.tileLayer>[1] extends never ? never : ReturnType<typeof L.map>)
      mapRef.current = map
    })
    return () => {
      if (mapRef.current) {
        (mapRef.current as { remove: () => void }).remove()
        mapRef.current = null
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const runQuery = useCallback(async () => {
    const L = (await import('leaflet')).default
    const map = mapRef.current as ReturnType<typeof L.map> | null
    if (!map) return
    setLoadingMap(true); setMapError(null)
    map.setView([lat, lng], 15)
    // clear old layers except tile
    map.eachLayer(layer => {
      if (!(layer as unknown as { _url?: string })._url) map.removeLayer(layer)
    })
    const homeIcon = L.divIcon({
      html:`<div style="background:#2563eb;width:14px;height:14px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,.4)"></div>`,
      iconSize:[14,14], iconAnchor:[7,7], className:'',
    })
    L.marker([lat,lng],{icon:homeIcon}).addTo(map).bindPopup(`<b>${ville||'Bien'}</b>`)
    L.circle([lat,lng],{radius:500,color:'#2563eb',fillColor:'#2563eb',fillOpacity:.05,weight:1.5,dashArray:'6 4'}).addTo(map)
    const q = `[out:json][timeout:15];(
      node["shop"~"supermarket|convenience|grocery|bakery"](around:500,${lat},${lng});
      node["amenity"~"pharmacy|chemist"](around:500,${lat},${lng});
      node["amenity"~"school|college|university|kindergarten"](around:500,${lat},${lng});
      node["highway"="bus_stop"](around:500,${lat},${lng});
      node["railway"~"station|halt|tram_stop|subway_entrance"](around:500,${lat},${lng});
      node["amenity"~"restaurant|cafe|fast_food|bar"](around:500,${lat},${lng});
      node["amenity"~"hospital|clinic|doctors|dentist"](around:500,${lat},${lng});
      node["amenity"="place_of_worship"]["religion"="muslim"](around:500,${lat},${lng});
      node["leisure"~"park|garden|playground"](around:500,${lat},${lng});
    );out body;`
    try {
      const res  = await fetch(`https://overpass-api.de/api/interpreter?data=${encodeURIComponent(q)}`,{signal:AbortSignal.timeout(18000)})
      if (!res.ok) throw new Error(`Overpass ${res.status}`)
      const json = await res.json()
      const found: {type:string;name:string}[] = []
      const seen = new Set<string>()
      for (const node of json.elements ?? []) {
        const t = classifyNode(node.tags ?? {})
        if (!t) continue
        const name = node.tags?.name ?? SERVICE_CFG[t]?.label ?? t
        found.push({type:t,name})
        seen.add(t)
        const cfg = SERVICE_CFG[t]
        const icon = L.divIcon({
          html:`<div title="${name}" style="background:${cfg.color};width:10px;height:10px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.3)"></div>`,
          iconSize:[10,10],iconAnchor:[5,5],className:'',
        })
        L.marker([node.lat,node.lon],{icon}).addTo(map).bindPopup(`<b>${name}</b><br><span style="color:${cfg.color}">${cfg.label}</span>`)
      }
      setDetected(found)
      const types = Array.from(seen)
      const s = types.reduce((a,t)=>a+(SERVICE_CFG[t]?.coeff??0),0)
      setScore(s)
      onServices(types)
    } catch(e) {
      const msg = e instanceof Error ? e.message : 'Erreur réseau'
      setMapError(`Impossible de charger les services (${msg})`)
      onServices([])
    } finally { setLoadingMap(false) }
  }, [lat, lng, ville, onServices])

  useEffect(() => { const t=setTimeout(runQuery,300); return ()=>clearTimeout(t) }, [runQuery])

  const grouped = detected.reduce<Record<string,number>>((a,s)=>({...a,[s.type]:(a[s.type]??0)+1}),{})
  const types = Object.keys(grouped)

  return (
    <div className="space-y-3">
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossOrigin="" />
      <div className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm">
        <div ref={divRef} style={{height:260}} />
        {loadingMap && (
          <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-[9999]">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              Détection des services…
            </div>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <span>Rayon d'analyse : <strong>500 m</strong></span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-blue-600 inline-block"/>Centre du bien</span>
      </div>
      {mapError && <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">{mapError}</p>}
      {!loadingMap && types.length > 0 && (
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-700">Services détectés ({detected.length} établissements)</p>
            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
              Score +{score}%
            </span>
          </div>
          <div className="grid grid-cols-1 gap-1.5">
            {types.map(t => (
              <div key={t} className="flex items-center gap-2 text-xs">
                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{background:SERVICE_CFG[t].color}}/>
                <span className="text-slate-600 flex-1">{SERVICE_CFG[t].label}</span>
                <span className="text-slate-400">{grouped[t]}×</span>
                <span className="font-semibold text-emerald-600">+{SERVICE_CFG[t].coeff}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {!loadingMap && types.length === 0 && !mapError && (
        <p className="text-xs text-slate-400 text-center py-1">Aucun service détecté dans un rayon de 500 m. <span className="text-slate-500">(Score proximité : 0%)</span></p>
      )}
      {!loadingMap && types.length > 0 && (
        <p className="text-xs text-slate-500 text-center">Score de proximité cumulé : <strong className="text-emerald-600">+{score}%</strong> appliqué sur le prix de référence</p>
      )}
    </div>
  )
}

// ── AgentReport sub-component ─────────────────────────────────────────────────
function AgentReport({ result }: { result: AgentResponse }) {
  const {
    mode, gouvernorat, ville, quartier, standing, type_bien, composition, superficie,
    valeur_saisie, valeur_totale_actuelle, prix_base, prix_reference_ajuste,
    diff_vs_marche_pct, statut_prix, taux_annuel, coeff_standing,
    score_attributs, score_proximite, attributs_actifs, services_detectes,
    horizons, tendance, risque, tension, analyse_marche, facteurs, recommandation,
  } = result
  const unite = mode === 'vente' ? 'TND/m²' : 'TND/mois'
  const locLabel = [quartier,ville,gouvernorat].filter(Boolean).join(', ')
  const standingLabel = standing.charAt(0).toUpperCase()+standing.slice(1)
  const labelBien = mode === 'vente'
    ? `${type_bien ? type_bien.charAt(0).toUpperCase()+type_bien.slice(1) : ''} · ${locLabel}`
    : `${composition} · ${locLabel}`
  const tendCfg = { hausse:{label:'Tendance haussière',cls:'bg-emerald-50 text-emerald-700 border-emerald-200'}, baisse:{label:'Tendance baissière',cls:'bg-red-50 text-red-600 border-red-200'}, stable:{label:'Marché stable',cls:'bg-slate-100 text-slate-600 border-slate-200'} }
  const { label: tendLabel, cls: tendCls } = tendCfg[tendance] ?? tendCfg.stable
  const risqueCfg = { Faible:{cls:'bg-emerald-100 text-emerald-700 border-emerald-200',dot:'bg-emerald-500'}, Modéré:{cls:'bg-amber-100 text-amber-700 border-amber-200',dot:'bg-amber-500'}, Élevé:{cls:'bg-red-100 text-red-600 border-red-200',dot:'bg-red-500'} }
  const { cls: rCls, dot: rDot } = risqueCfg[risque] ?? risqueCfg['Modéré']
  const statutColor = statut_prix.includes('sous') ? 'text-sky-600' : statut_prix.includes('surévalué') ? 'text-amber-600' : 'text-emerald-600'
  const HORIZONS = [
    {key:'6'  as const, label:'+6 mois',  bg:'bg-sky-50',    text:'text-sky-700'    },
    {key:'12' as const, label:'+12 mois', bg:'bg-blue-50',   text:'text-blue-700'   },
    {key:'18' as const, label:'+18 mois', bg:'bg-violet-50', text:'text-violet-700' },
    {key:'24' as const, label:'+24 mois', bg:'bg-indigo-50', text:'text-indigo-700' },
  ]
  const totalScore = score_attributs + score_proximite + (coeff_standing - 1)
  const maxScore = 0.60
  function ScoreBar({label,value,color}:{label:string;value:number;color:string}) {
    return (
      <div className="space-y-1">
        <div className="flex justify-between text-xs"><span className="text-slate-600">{label}</span><span className="font-semibold" style={{color}}>+{FMT2.format(value*100)}%</span></div>
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden"><div className="h-full rounded-full transition-all duration-700" style={{width:`${Math.min(100,(value/maxScore)*100)}%`,background:color}}/></div>
      </div>
    )
  }
  const diffClamped = Math.max(-50,Math.min(50,diff_vs_marche_pct))
  const diffPct = ((diffClamped+50)/100)*100
  const diffColor = diff_vs_marche_pct < -5 ? 'bg-sky-500' : diff_vs_marche_pct > 5 ? 'bg-amber-500' : 'bg-emerald-500'

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">Rapport d'analyse</h2>
            <p className="text-sm text-slate-500 mt-0.5">{labelBien}</p>
            <p className="text-xs text-slate-400 mt-0.5">Standing : <span className="font-semibold text-slate-600">{standingLabel}</span>{quartier && <> · Quartier : <span className="font-semibold text-slate-600">{quartier}</span></>}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${tendCls}`}>{tendLabel}</span>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${rCls}`}><span className={`w-2 h-2 rounded-full ${rDot}`}/>Risque {risque}</span>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
          <div><span className="font-medium text-slate-700">Tension :</span> <span className="font-semibold text-blue-600 capitalize">{tension}</span></div>
          <div><span className="font-medium text-slate-700">Croissance annuelle :</span> <span className="font-semibold text-emerald-600">{FMT2.format(taux_annuel)}%/an</span></div>
          {mode === 'vente' && superficie && <div><span className="font-medium text-slate-700">Valeur totale actuelle :</span> <span className="font-semibold text-slate-800">{FMT.format(valeur_totale_actuelle ?? 0)} TND</span></div>}
        </div>
      </div>
      {/* Score localisation */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">Score de localisation</h3>
        <div className="space-y-3 mb-4">
          <ScoreBar label={`Standing ${standingLabel} (×${coeff_standing.toFixed(2)})`} value={Math.max(0,coeff_standing-1)} color="#6366f1"/>
          <ScoreBar label={`Attributs du bien (${Object.keys(attributs_actifs).length} coché${Object.keys(attributs_actifs).length>1?'s':''})`} value={score_attributs} color="#3b82f6"/>
          <ScoreBar label={`Services de proximité (${Object.keys(services_detectes).length} type${Object.keys(services_detectes).length>1?'s':''})`} value={score_proximite} color="#10b981"/>
        </div>
        <div className="grid grid-cols-3 gap-3 text-center text-xs border-t pt-3 border-slate-100">
          <div className="rounded-lg bg-violet-50 p-2"><p className="text-violet-500 mb-0.5">Prix de base</p><p className="font-bold text-violet-700">{FMT.format(prix_base)}</p><p className="text-violet-400">{unite}</p></div>
          <div className="rounded-lg bg-blue-50 p-2"><p className="text-blue-500 mb-0.5">Après attributs</p><p className="font-bold text-blue-700">{FMT.format(prix_base*(1+score_attributs))}</p><p className="text-blue-400">{unite}</p></div>
          <div className="rounded-lg bg-emerald-50 p-2"><p className="text-emerald-500 mb-0.5">Référence ajustée</p><p className="font-bold text-emerald-700">{FMT.format(prix_reference_ajuste)}</p><p className="text-emerald-400">{unite}</p></div>
        </div>
        {Object.keys(attributs_actifs).length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {Object.entries(attributs_actifs).map(([k,v])=>(
              <span key={k} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full border border-blue-200">{ATTR_LABELS[k]??k} +{FMT2.format(v*100)}%</span>
            ))}
          </div>
        )}
        {Object.keys(services_detectes).length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {Object.entries(services_detectes).map(([k,v])=>(
              <span key={k} className="px-2 py-0.5 text-white text-xs rounded-full" style={{background:SERVICE_CFG[k]?.color??'#64748b'}}>{SERVICE_CFG[k]?.label??k} +{FMT2.format(v*100)}%</span>
            ))}
          </div>
        )}
        {totalScore > 0 && <p className="text-xs text-slate-400 text-right mt-3">Score total appliqué : <strong className="text-slate-600">+{FMT2.format(totalScore*100)}%</strong> sur le prix référence gouvernorat</p>}
      </div>
      {/* Positionnement */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">Positionnement marché</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl bg-slate-50 p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">{mode==='vente'?'Votre prix/m²':'Votre loyer'}</p>
            <p className="text-2xl font-bold text-slate-800">{FMT.format(valeur_saisie)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{unite}</p>
          </div>
          <div className="rounded-xl bg-emerald-50 p-4 text-center">
            <p className="text-xs text-emerald-500 mb-1">Référence {standingLabel} · {ville||gouvernorat}</p>
            <p className="text-2xl font-bold text-emerald-700">{FMT.format(prix_reference_ajuste)}</p>
            <p className="text-xs text-emerald-400 mt-0.5">{unite}</p>
          </div>
        </div>
        <div className="mt-4 text-center">
          <span className={`text-sm font-semibold capitalize ${statutColor}`}>{statut_prix}</span>
          <span className="text-sm text-slate-500 ml-2">({diff_vs_marche_pct>0?'+':''}{FMT2.format(diff_vs_marche_pct)}% vs référence ajustée)</span>
          <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden mt-2">
            <div className={`absolute top-0 h-full w-1 ${diffColor} rounded-full transition-all duration-700`} style={{left:`calc(${diffPct}% - 2px)`}}/>
            <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400 opacity-40"/>
          </div>
          <div className="flex justify-between text-xs text-slate-400 mt-1"><span>−50%</span><span>Référence marché</span><span>+50%</span></div>
        </div>
      </div>
      {/* Horizons */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">Prévisions de prix</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {HORIZONS.map(({key,label,bg,text})=>{
            const h = horizons[key]
            return (
              <div key={key} className={`rounded-xl ${bg} p-4 text-center`}>
                <p className={`text-xs font-medium mb-1 ${text}`}>{label}</p>
                <p className={`text-xl font-bold ${text}`}>{FMT.format(h.valeur)}</p>
                <p className="text-xs text-slate-400 mt-0.5">{unite}</p>
                <div className="mt-2">
                  <span className={`text-xs font-bold ${h.variation_pct>=0?'text-emerald-600':'text-red-500'}`}>{h.variation_pct>=0?'+':''}{FMT2.format(h.variation_pct)}%</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      {/* Analyse marché */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-3">Analyse du marché local</h3>
        <p className="text-sm text-slate-600 leading-relaxed">{analyse_marche}</p>
        <div className="mt-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Facteurs clés</p>
          <div className="flex flex-wrap gap-2">
            {facteurs.map((f,i)=>(
              <span key={i} className="inline-block px-3 py-1 bg-blue-50 text-blue-700 text-xs rounded-full border border-blue-200">{f}</span>
            ))}
          </div>
        </div>
      </div>
      {/* Recommandation */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl shadow-md p-6 text-white">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center text-sm font-bold">IA</div>
          <h3 className="text-base font-semibold">Recommandation de l'agent</h3>
        </div>
        <p className="text-sm leading-relaxed text-blue-50">{recommandation}</p>
      </div>
    </div>
  )
}

// ── ForecastChart sub-component ───────────────────────────────────────────────
function ForecastChart({ points, valeurActuelle, unite, titre }: {
  points: ForecastPoint[]; valeurActuelle: number; unite: string; titre?: string
}) {
  const today = new Date().toISOString().slice(0,7)
  const todayLabel = fmtDate(today+'-01')
  const data = [
    { label:'Aujourd\'hui', prix:valeurActuelle, ic_bas:undefined as number|undefined, ic_haut:undefined as number|undefined, isToday:true },
    ...points.map(p=>({ label:fmtDate(p.date), prix:p.prix_predit, ic_bas:p.ic_bas??undefined, ic_haut:p.ic_haut??undefined, isToday:false })),
  ]
  const step = Math.max(1, Math.floor(data.length/8))
  function CT({ active, payload, label }: { active?: boolean; payload?: {payload:{prix:number;ic_bas?:number;ic_haut?:number}}[]; label?: string }) {
    if (!active||!payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-lg text-sm">
        <p className="font-semibold text-slate-700 mb-1">{label}</p>
        <p className="text-blue-600">Prédit : <strong>{FMT.format(d.prix)}</strong></p>
        {d.ic_bas != null && d.ic_haut != null && <p className="text-slate-400 text-xs mt-1">IC 90% : [{FMT.format(d.ic_bas)} – {FMT.format(d.ic_haut)}]</p>}
      </div>
    )
  }
  return (
    <div className="bg-white rounded-2xl shadow-md p-6">
      <h2 className="text-xl font-semibold text-slate-800 mb-1">{titre ?? 'Évolution prévue sur 24 mois'}</h2>
      <p className="text-xs text-slate-400 mb-4">Unité : {unite} · IC 90% affiché</p>
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{top:8,right:24,left:8,bottom:8}}>
          <defs>
            <linearGradient id="icGrad2" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.12}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9"/>
          <XAxis dataKey="label" tick={{fontSize:11,fill:'#94a3b8'}} interval={step-1}/>
          <YAxis tickFormatter={v=>FMT.format(v)} tick={{fontSize:11,fill:'#94a3b8'}} width={78}/>
          <Tooltip content={<CT/>}/>
          <Legend wrapperStyle={{fontSize:12}}/>
          <Area type="monotone" dataKey="ic_haut" stroke="none" fill="url(#icGrad2)" legendType="none" connectNulls/>
          <Area type="monotone" dataKey="ic_bas"  stroke="none" fill="#ffffff"        legendType="none" connectNulls/>
          <Line type="monotone" dataKey="prix" stroke="#2563eb" strokeWidth={2.5}
            dot={(props: { payload: { isToday: boolean }; cx: number; cy: number; key: string }) =>
              props.payload.isToday
                ? <circle key={props.key} cx={props.cx} cy={props.cy} r={6} fill="#f59e0b" stroke="#fff" strokeWidth={2}/>
                : <circle key={props.key} cx={props.cx} cy={props.cy} r={0}/>
            }
            activeDot={{r:5}} name={`Valeur prédite (${unite})`} connectNulls
          />
          <ReferenceLine x={todayLabel} stroke="#f59e0b" strokeDasharray="4 3" label={{value:'Auj.',fill:'#f59e0b',fontSize:10}}/>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Mode = 'vente' | 'location'

function ForecastContent() {
  // Form state
  const [mode, setMode]           = useState<Mode>('vente')
  const [gouvernorat, setGouv]    = useState('Tunis')
  const [villes, setVilles]       = useState<string[]>([])
  const [ville, setVille]         = useState('')
  const [coords, setCoords]       = useState<Record<string,[number,number]>>({})
  const [quartier, setQuartier]   = useState('')
  const [standing, setStanding]   = useState('intermédiaire')
  const [typeBien, setTypeBien]   = useState('appartement')
  const [superficie, setSuper]    = useState('90')
  const [prixM2, setPrixM2]       = useState('3500')
  const [composition, setComp]    = useState('S+2')
  const [loyer, setLoyer]         = useState('1200')
  const [attributs, setAttributs] = useState<Set<string>>(new Set())
  const [showAttrs, setShowAttrs] = useState(false)
  const [services, setServices]   = useState<string[]>([])
  const [formError, setFormError] = useState<string|null>(null)
  // Result state
  const [loading, setLoading]     = useState(false)
  const [result, setResult]       = useState<AgentResponse|null>(null)
  const [error, setError]         = useState<string|null>(null)

  // Load villes when gouvernorat changes
  useEffect(() => {
    setVille(''); setServices([])
    fetch(`${BASE}/api/villes/${encodeURIComponent(gouvernorat)}`)
      .then(r=>r.json())
      .then(d=>{ setVilles(d.villes??[]); setCoords(d.coords??{}); if(d.villes?.length) setVille(d.villes[0]) })
      .catch(()=>setVilles([]))
  }, [gouvernorat])

  const currentCoords = ville ? coords[ville] : null

  const attrList = mode === 'vente' ? ATTRS_VENTE : ATTRS_LOC
  const scoreAttrs = Array.from(attributs).reduce((s,k)=>{
    const found = attrList.find(a=>a.key===k)
    return s+(found ? parseInt(found.pct) : 0)
  }, 0)

  function toggleAttr(k: string) {
    setAttributs(prev=>{ const n=new Set(prev); n.has(k)?n.delete(k):n.add(k); return n })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setFormError(null); setError(null)
    const geo = { gouvernorat, ville, quartier, standing }
    const attrList2 = Array.from(attributs)

    let body: Record<string,unknown>
    if (mode === 'vente') {
      const s = parseFloat(superficie), p = parseFloat(prixM2)
      if (!superficie||isNaN(s)||s<=0) { setFormError('Superficie invalide (> 0 m²).'); return }
      if (!prixM2||isNaN(p)||p<=0)     { setFormError('Prix au m² invalide (> 0 TND).'); return }
      body = { ...geo, type_bien:typeBien, superficie:s, prix_m2_saisi:p, attributs_bien:attrList2, services_proximite:services }
    } else {
      const l = parseFloat(loyer)
      if (!loyer||isNaN(l)||l<=0) { setFormError('Loyer invalide (> 0 TND).'); return }
      body = { ...geo, composition, loyer_saisi:l, attributs_bien:attrList2, services_proximite:services }
    }

    setLoading(true)
    try {
      const endpoint = mode === 'vente' ? '/api/analyze/vente' : '/api/analyze/location'
      const res = await fetch(`${BASE}${endpoint}`,{ method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) })
      if (!res.ok) throw new Error(`Erreur ${res.status}`)
      setResult(await res.json())
    } catch(e) {
      setError(e instanceof Error ? e.message : 'Erreur lors de l\'analyse.')
    } finally { setLoading(false) }
  }

  const unite = result?.mode === 'location' ? 'TND/mois' : 'TND/m²'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 to-blue-50 -m-6 p-6">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-lg">IF</div>
          <div>
            <h1 className="text-lg font-bold text-slate-800 leading-tight">ImmoForecast TN</h1>
            <p className="text-xs text-slate-500">Agent IA · Prévision immobilière · 24 gouvernorats · 3 niveaux géo · Carte Overpass</p>
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6 items-start">

        {/* ── LEFT: Form ── */}
        <div className="space-y-4">
          <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-md p-6 space-y-5">
            <h2 className="text-xl font-semibold text-slate-800">Paramètres du bien</h2>

            {/* Mode toggle */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Mode d'analyse</label>
              <div className="flex rounded-lg overflow-hidden border border-slate-300">
                {(['vente','location'] as Mode[]).map(m=>(
                  <button key={m} type="button"
                    onClick={()=>{ setMode(m); setAttributs(new Set()); setFormError(null) }}
                    className={`flex-1 py-2 text-sm font-semibold transition-colors ${mode===m?'bg-blue-600 text-white':'bg-white text-slate-600 hover:bg-slate-50'}`}>
                    {m==='vente'?'Vente (prix/m²)':'Location (loyer)'}
                  </button>
                ))}
              </div>
            </div>

            {/* Niveau 1 */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                <span className="text-xs font-bold text-blue-600 uppercase tracking-wide mr-1">Niveau 1</span>Gouvernorat
              </label>
              <select value={gouvernorat} onChange={e=>setGouv(e.target.value)} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                {GOUVERNORATS.map(g=><option key={g} value={g}>{g}</option>)}
              </select>
            </div>

            {/* Niveau 2 */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                <span className="text-xs font-bold text-blue-600 uppercase tracking-wide mr-1">Niveau 2</span>Ville / Délégation
              </label>
              <select value={ville} onChange={e=>{ setVille(e.target.value); setServices([]) }} disabled={villes.length===0}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50">
                {villes.length===0 ? <option>Chargement…</option> : villes.map(v=><option key={v} value={v}>{v}</option>)}
              </select>
            </div>

            {/* Niveau 3 */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-700">
                <span className="text-xs font-bold text-blue-600 uppercase tracking-wide mr-1">Niveau 3</span>Quartier &amp; Standing
              </label>
              <input type="text" value={quartier} onChange={e=>setQuartier(e.target.value)}
                placeholder="Nom du quartier (facultatif)"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
              <div className="grid grid-cols-5 gap-1.5">
                {STANDINGS.map(s=>(
                  <button key={s.value} type="button" onClick={()=>setStanding(s.value)}
                    className={`relative rounded-lg px-1.5 py-2 text-center text-xs font-semibold border-2 transition-all ${standing===s.value ? s.color+' ring-2 ring-offset-1 ring-blue-500' : 'bg-white border-slate-200 text-slate-500 hover:border-slate-400'}`}>
                    <div>{s.label}</div>
                    <div className="text-[10px] opacity-70 mt-0.5">{s.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Vente fields */}
            {mode === 'vente' && <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type de bien</label>
                <select value={typeBien} onChange={e=>setTypeBien(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  {TYPES_BIEN.map(t=><option key={t} value={t}>{t.charAt(0).toUpperCase()+t.slice(1)}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Superficie <span className="text-slate-400">(m²)</span></label>
                  <input type="number" value={superficie} onChange={e=>setSuper(e.target.value)} min="1" placeholder="ex: 90"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Prix au m² <span className="text-slate-400">(TND)</span></label>
                  <input type="number" value={prixM2} onChange={e=>setPrixM2(e.target.value)} min="1" placeholder="ex: 3500"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                </div>
              </div>
            </>}

            {/* Location fields */}
            {mode === 'location' && <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Composition du logement</label>
                <div className="grid grid-cols-4 gap-2">
                  {COMPS.map(c=>(
                    <button key={c} type="button" onClick={()=>setComp(c)}
                      className={`py-2 rounded-lg text-sm font-semibold border transition-colors ${composition===c?'bg-blue-600 text-white border-blue-600':'bg-white text-slate-600 border-slate-300 hover:border-blue-400'}`}>
                      {c}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Loyer mensuel <span className="text-slate-400">(TND)</span></label>
                <input type="number" value={loyer} onChange={e=>setLoyer(e.target.value)} min="1" placeholder="ex: 1200"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"/>
              </div>
            </>}

            {/* Attributs */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <button type="button" onClick={()=>setShowAttrs(v=>!v)}
                className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-700">Attributs du bien</span>
                  <span className="text-xs text-slate-400">(Catégorie A)</span>
                  {attributs.size>0 && <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-semibold">{attributs.size} coché{attributs.size>1?'s':''}</span>}
                </div>
                <div className="flex items-center gap-2">
                  {scoreAttrs>0 && <span className="text-emerald-600 font-bold text-xs">+{scoreAttrs}%</span>}
                  <svg className={`w-4 h-4 text-slate-400 transition-transform ${showAttrs?'rotate-180':''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/>
                  </svg>
                </div>
              </button>
              {showAttrs && (
                <div className="px-4 py-3 grid grid-cols-1 gap-2">
                  {attrList.map(a=>(
                    <label key={a.key} className="flex items-center gap-3 cursor-pointer group">
                      <input type="checkbox" checked={attributs.has(a.key)} onChange={()=>toggleAttr(a.key)}
                        className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"/>
                      <span className="flex-1 text-sm text-slate-700 group-hover:text-blue-700 transition-colors">{a.label}</span>
                      <span className="text-xs font-semibold text-emerald-600">{a.pct}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* ProximityMap */}
            {currentCoords && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-slate-700">Services de proximité</p>
                  <span className="text-xs text-slate-400">(Catégorie B — détection automatique)</span>
                </div>
                <ProximityMap lat={currentCoords[0]} lng={currentCoords[1]} ville={ville} onServices={setServices}/>
                {services.length>0 && (
                  <p className="text-xs text-emerald-600 text-center">
                    {services.length} type{services.length>1?'s':''} de service détecté{services.length>1?'s':''} — inclus dans le calcul
                  </p>
                )}
              </div>
            )}

            {formError && <p className="text-red-500 text-xs">{formError}</p>}

            <button type="submit" disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-xl py-3 transition-colors">
              {loading ? 'Analyse en cours…' : 'Lancer l\'analyse'}
            </button>
          </form>

          {/* Info box */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-700 space-y-1.5">
            <p className="font-semibold">Comment fonctionne l'agent ?</p>
            <p><strong>Niveau 1 (Gouvernorat)</strong> — taux de croissance et profil de marché calibrés.</p>
            <p><strong>Niveau 2 (Standing)</strong> — coefficient multiplicateur sur le prix de référence (populaire ×0.75 → luxe ×1.70).</p>
            <p><strong>Catégorie A (Attributs)</strong> — chaque équipement coché ajoute un pourcentage cumulatif.</p>
            <p><strong>Catégorie B (Proximité)</strong> — détection automatique des services dans un rayon de 500 m via OpenStreetMap.</p>
          </div>
        </div>

        {/* ── RIGHT: Results ── */}
        <div className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              <strong>Erreur :</strong> {error}
            </div>
          )}
          {loading && (
            <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"/>
              <p className="text-slate-500 text-sm">L'agent analyse le marché…</p>
            </div>
          )}
          {result && !loading && (
            <>
              <AgentReport result={result}/>
              <ForecastChart
                points={result.points}
                valeurActuelle={result.valeur_saisie}
                unite={unite}
                titre={
                  result.mode==='vente'
                    ? `Évolution du prix au m² — ${[result.quartier,result.ville,result.gouvernorat].filter(Boolean).join(', ')}`
                    : `Évolution du loyer ${result.composition} — ${[result.ville,result.gouvernorat].filter(Boolean).join(', ')}`
                }
              />
            </>
          )}
          {!result && !loading && !error && (
            <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center gap-3 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-14 h-14 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3v18h18M9 17l4-8 4 4 2-6"/>
              </svg>
              <p className="text-sm text-center">Sélectionnez un gouvernorat, une ville, le standing du quartier, puis cliquez sur <strong>Lancer l'analyse</strong>.</p>
            </div>
          )}
        </div>
      </div>

      <footer className="text-center py-6 text-xs text-slate-400 max-w-6xl mx-auto mt-6">
        NeuroNova · Esprit PI 4DS10 2025-2026 · ImmoForecast TN v3
      </footer>
    </div>
  )
}

export default function ForecastPage() {
  return <SubscriptionGuard><ForecastContent /></SubscriptionGuard>
}
