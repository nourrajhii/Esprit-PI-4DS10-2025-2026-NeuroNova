'use client'
import { useEffect, useRef, useState } from 'react'
import SubscriptionGuard from '@/components/SubscriptionGuard'
import {
  Box, Download, Loader2, RotateCcw, Upload, Wand2,
  Type, Layers, Image as ImageIcon, Sparkles, Info,
} from 'lucide-react'

const API = process.env.NEXT_PUBLIC_VILLA3D_API_URL || 'http://localhost:8056'

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string; alt?: string; 'auto-rotate'?: boolean | string
        'camera-controls'?: boolean | string; 'shadow-intensity'?: string
        'environment-image'?: string; exposure?: string
        style?: React.CSSProperties
      }
    }
  }
}

type Mode  = 'sd+tripo' | 'direct' | 'multiview' | 'text'
type Step  = 'idle' | 'generating2d' | 'done2d' | 'converting3d' | 'done3d' | 'error'

const MODES: { id: Mode; label: string; icon: React.ElementType; desc: string }[] = [
  { id: 'text',      label: 'Texte → 3D',       icon: Type,      desc: 'Décrivez un bâtiment, Tripo3D le génère' },
  { id: 'direct',    label: 'Photo → 3D',        icon: ImageIcon, desc: 'Image directement vers Tripo3D v3.1' },
  { id: 'multiview', label: 'Photo → 3D HD',     icon: Layers,    desc: 'Pipeline multiview 4 angles — meilleure qualité' },
  { id: 'sd+tripo',  label: 'Terrain → Villa',   icon: Wand2,     desc: 'SD génère la façade, Tripo3D la modélise' },
]

// Tripo3D model versions from the API docs
const MODEL_VERSIONS = [
  { value: 'v3.1-20260211', label: 'v3.1 (recommandé)' },
  { value: 'v3.0-20250812', label: 'v3.0' },
  { value: 'v2.5-20250123', label: 'v2.5' },
  { value: 'P1-20260311',   label: 'P1 (low-poly, rapide)' },
]

function Villa3DContent() {
  const [apiOnline, setApiOnline]   = useState<boolean | null>(null)
  const [sdStatus,  setSdStatus]    = useState<'loading' | 'ready' | 'error' | null>(null)
  const [mode,      setMode]        = useState<Mode>('text')
  const [step,      setStep]        = useState<Step>('idle')
  const [errorMsg,  setErrorMsg]    = useState('')
  const [progress,  setProgress]    = useState('')

  // Image input
  const [inputFile,    setInputFile]    = useState<File | null>(null)
  const [inputPreview, setInputPreview] = useState<string | null>(null)
  const [image2d,      setImage2d]      = useState<string | null>(null)

  // 3D output — glbSrc is a blob: URL (avoids cross-origin download/CORS issues)
  const [glbSrc,  setGlbSrc]  = useState<string | null>(null)
  const [glbFile, setGlbFile] = useState<string | null>(null)
  const [glbSize, setGlbSize] = useState<number | null>(null)

  // Fetch GLB (or convert a base64 data URL) → blob URL so model-viewer + download both work
  async function _applyGlb(urlOrDataUrl: string, filename: string, sizeKb: number | null) {
    let blob: Blob
    if (urlOrDataUrl.startsWith('data:')) {
      // Old server format: base64 data URL — convert to blob directly
      const res = await fetch(urlOrDataUrl)
      blob = await res.blob()
    } else {
      // New server format: HTTP URL to /download/{file}
      const res = await fetch(urlOrDataUrl)
      if (!res.ok) throw new Error(`GLB download failed — HTTP ${res.status}`)
      blob = await res.blob()
    }
    const blobUrl = URL.createObjectURL(blob)
    setGlbSrc(prev => { if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev); return blobUrl })
    setGlbFile(filename)
    setGlbSize(sizeKb ?? Math.round(blob.size / 1024))
  }

  // Parse either old { glb, filename } or new { url, filename, size_kb } API response
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async function _handleGlbResponse(d: any) {
    const filename: string = d.filename || 'villa.glb'
    const sizeKb: number | null = d.size_kb ?? null
    if (d.url) {
      await _applyGlb(`${API}${d.url}`, filename, sizeKb)
    } else if (d.glb) {
      await _applyGlb(d.glb, filename, sizeKb)
    } else {
      throw new Error('Réponse API invalide — aucun modèle GLB reçu')
    }
  }

  // Prompt controls
  const [sdPrompt,       setSdPrompt]       = useState('')
  const [textPrompt,     setTextPrompt]     = useState('')
  const [negativePrompt, setNegativePrompt] = useState('cartoon, anime, flat, low quality, blurry, sketch, watermark')
  const [modelVersion,   setModelVersion]   = useState('v3.1-20260211')
  const [showAdvanced,   setShowAdvanced]   = useState(false)

  const fileRef = useRef<HTMLInputElement>(null)

  // ── Health polling ────────────────────────────────────────────────────────
  useEffect(() => {
    let iv: ReturnType<typeof setInterval>
    async function check() {
      try {
        const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) })
        if (!r.ok) { setApiOnline(false); return }
        setApiOnline(true)
        const d = await r.json()
        setSdStatus(d.sd_status ?? (d.sd_available ? 'ready' : 'loading'))
        if (d.sd_status === 'ready') clearInterval(iv)
      } catch { setApiOnline(false) }
    }
    check(); iv = setInterval(check, 6000)
    return () => clearInterval(iv)
  }, [])

  // ── model-viewer script ───────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined' || document.querySelector('script[data-mv]')) return
    const s = document.createElement('script')
    s.type = 'module'; s.dataset.mv = '1'
    s.src = 'https://unpkg.com/@google/model-viewer@3.4.0/dist/model-viewer.min.js'
    document.head.appendChild(s)
  }, [])

  // ── File handling ─────────────────────────────────────────────────────────
  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return
    setInputFile(f); setInputPreview(URL.createObjectURL(f))
    setImage2d(null); setGlbSrc(null); setGlbFile(null)
    setStep('idle'); setErrorMsg('')
  }

  function reset() {
    setGlbSrc(prev => { if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev); return null })
    setStep('idle'); setInputFile(null); setInputPreview(null)
    setImage2d(null); setGlbFile(null); setGlbSize(null)
    setErrorMsg(''); setProgress('')
    if (fileRef.current) fileRef.current.value = ''
  }

  // ── Progress ticker helper ────────────────────────────────────────────────
  function startTicker(stages: string[]) {
    let i = 0; setProgress(stages[0])
    const t = setInterval(() => { i = Math.min(i + 1, stages.length - 1); setProgress(stages[i]) }, 25000)
    return t
  }

  // ── Text → 3D ────────────────────────────────────────────────────────────
  async function runTextTo3D() {
    if (!textPrompt.trim()) return
    setStep('converting3d'); setErrorMsg('')
    const ticker = startTicker([
      'Envoi du prompt à Tripo3D…',
      'Création du modèle 3D…',
      'Ajout des textures PBR…',
      'Téléchargement GLB…',
    ])
    try {
      const r = await fetch(`${API}/generate3d-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: textPrompt.trim(),
          negative_prompt: negativePrompt,
          model_version: modelVersion,
        }),
      })
      clearInterval(ticker)
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Erreur text-to-3D') }
      const d = await r.json()
      await _handleGlbResponse(d)
      setStep('done3d'); setProgress('')
    } catch (e: unknown) {
      clearInterval(ticker)
      setErrorMsg(e instanceof Error ? e.message : 'Erreur inconnue'); setStep('error')
    }
  }

  // ── Image → 3D (direct) ──────────────────────────────────────────────────
  async function runDirect() {
    if (!inputFile) return
    setStep('converting3d'); setErrorMsg('')
    const ticker = startTicker([
      'Upload image vers Tripo3D…', 'Reconstruction 3D…',
      'Textures PBR…', 'Finalisation GLB…',
    ])
    const fd = new FormData(); fd.append('file', inputFile)
    try {
      const r = await fetch(`${API}/convert3d-direct`, { method: 'POST', body: fd })
      clearInterval(ticker)
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Erreur 3D direct') }
      const d = await r.json()
      await _handleGlbResponse(d)
      setStep('done3d'); setProgress('')
    } catch (e: unknown) {
      clearInterval(ticker)
      setErrorMsg(e instanceof Error ? e.message : 'Erreur inconnue'); setStep('error')
    }
  }

  // ── Image → 3D (multiview HD) ─────────────────────────────────────────────
  async function runMultiview() {
    if (!inputFile) return
    setStep('converting3d'); setErrorMsg('')
    const ticker = startTicker([
      'Upload image…',
      'Génération 4 vues (avant/gauche/arrière/droite)…',
      'Reconstruction multiview → 3D…',
      'Textures PBR haute résolution…',
      'Finalisation GLB…',
    ])
    const fd = new FormData(); fd.append('file', inputFile)
    try {
      const r = await fetch(`${API}/convert3d-multiview`, { method: 'POST', body: fd })
      clearInterval(ticker)
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Erreur multiview') }
      const d = await r.json()
      await _handleGlbResponse(d)
      setStep('done3d'); setProgress('')
    } catch (e: unknown) {
      clearInterval(ticker)
      setErrorMsg(e instanceof Error ? e.message : 'Erreur inconnue'); setStep('error')
    }
  }

  // ── SD → villa 2D ────────────────────────────────────────────────────────
  async function runGenerate2D() {
    if (!inputFile) return
    setStep('generating2d'); setErrorMsg(''); setProgress('Génération villa 2D via Stable Diffusion…')
    const fd = new FormData(); fd.append('file', inputFile)
    if (sdPrompt.trim()) fd.append('prompt', sdPrompt.trim())
    try {
      const r = await fetch(`${API}/generate2d`, { method: 'POST', body: fd })
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Erreur 2D') }
      const d = await r.json()
      setImage2d(d.image); setStep('done2d'); setProgress('')
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : 'Erreur'); setStep('error')
    }
  }

  // ── SD → 3D ──────────────────────────────────────────────────────────────
  async function runConvert3D() {
    setStep('converting3d'); setErrorMsg('')
    const ticker = startTicker([
      'Upload villa 2D vers Tripo3D…', 'Reconstruction 3D…',
      'Textures PBR…', 'Téléchargement GLB…',
    ])
    try {
      const r = await fetch(`${API}/convert3d`, { method: 'POST' })
      clearInterval(ticker)
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Erreur 3D') }
      const d = await r.json()
      await _handleGlbResponse(d)
      setStep('done3d'); setProgress('')
    } catch (e: unknown) {
      clearInterval(ticker)
      setErrorMsg(e instanceof Error ? e.message : 'Erreur'); setStep('error')
    }
  }

  const isRunning = step === 'generating2d' || step === 'converting3d'
  const needsImage = mode === 'direct' || mode === 'multiview' || mode === 'sd+tripo'

  return (
    <div className="space-y-5">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary mb-2">
            <Box className="h-3.5 w-3.5" /> Agent exclusif investisseur · Tripo3D v3.1
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Générateur 3D Immobilier</h1>
          <p className="mt-1 text-sm text-slate-500">
            Créez des modèles 3D interactifs depuis une description textuelle, une photo, ou un terrain.
          </p>
        </div>
        <div className="flex flex-col gap-1 items-end text-xs">
          <span className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border font-medium ${
            apiOnline === true ? 'bg-green-50 border-green-200 text-green-700' :
            apiOnline === false ? 'bg-red-50 border-red-200 text-red-700' :
            'bg-slate-50 border-slate-200 text-slate-500'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${apiOnline ? 'bg-green-500' : apiOnline === false ? 'bg-red-500' : 'bg-slate-400'}`} />
            {apiOnline === null ? 'Vérification…' : apiOnline ? 'API connectée' : 'API hors ligne'}
          </span>
          {apiOnline && sdStatus && (
            <span className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border font-medium ${
              sdStatus === 'ready' ? 'bg-green-50 border-green-200 text-green-700' :
              sdStatus === 'error' ? 'bg-red-50 border-red-200 text-red-700' :
              'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
              {sdStatus !== 'ready' && <Loader2 className="w-3 h-3 animate-spin" />}
              {sdStatus === 'ready' ? '✓ SD+LoRA prêt' : sdStatus === 'error' ? '✗ SD erreur' : 'SD chargement…'}
            </span>
          )}
        </div>
      </div>

      {/* ── Mode selector ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {MODES.map(({ id, label, icon: Icon, desc }) => (
          <button key={id} onClick={() => { setMode(id); reset() }}
            className={`flex flex-col items-start gap-1.5 p-3 rounded-xl border text-left transition-all ${
              mode === id
                ? 'border-primary bg-primary/5 shadow-sm ring-1 ring-primary/20'
                : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
            }`}>
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${mode === id ? 'bg-primary text-white' : 'bg-slate-100 text-slate-500'}`}>
              <Icon className="w-4 h-4" />
            </div>
            <p className={`text-xs font-semibold leading-none ${mode === id ? 'text-primary' : 'text-slate-700'}`}>{label}</p>
            <p className="text-[10px] text-slate-400 leading-snug">{desc}</p>
          </button>
        ))}
      </div>

      {/* ── API status banner ───────────────────────────────────────────── */}
      {apiOnline === false && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 flex items-start gap-3">
          <Loader2 className="w-4 h-4 mt-0.5 shrink-0 animate-spin text-amber-600" />
          <div>
            <p className="font-semibold">Villa3D API en cours de démarrage…</p>
            <p className="text-xs mt-1 text-amber-700">
              Le service démarre automatiquement. Rechargement automatique toutes les 6 s.
            </p>
          </div>
        </div>
      )}
      {apiOnline === true && sdStatus === 'loading' && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 flex items-center gap-3">
          <Loader2 className="w-4 h-4 shrink-0 animate-spin text-blue-500" />
          <span>Chargement du modèle Stable Diffusion + LoRA — prêt dans 2–5 min. Vous pouvez déjà utiliser les modes <strong>Texte → 3D</strong> et <strong>Photo → 3D</strong>.</span>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* ── Left: input panel ─────────────────────────────────────────── */}
        <div className="space-y-4">

          {/* TEXT MODE */}
          {mode === 'text' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Type className="w-4 h-4 text-primary" /> Description du modèle 3D
              </h2>
              <div>
                <textarea
                  value={textPrompt}
                  onChange={e => setTextPrompt(e.target.value)}
                  rows={4}
                  placeholder="Ex: modern Mediterranean villa with white stucco walls, terracotta roof tiles, arched windows, swimming pool, palm trees, photorealistic architectural render…"
                  className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary bg-slate-50"
                />
                <p className="text-[10px] text-slate-400 mt-1">{textPrompt.length}/1024 — soyez précis sur le style, les matériaux, la forme</p>
              </div>

              {/* Model version */}
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1">Version du modèle Tripo3D</label>
                <select value={modelVersion} onChange={e => setModelVersion(e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/30 bg-slate-50">
                  {MODEL_VERSIONS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
                </select>
              </div>

              {/* Advanced */}
              <button onClick={() => setShowAdvanced(v => !v)}
                className="text-xs text-primary flex items-center gap-1 hover:underline">
                <Info className="w-3 h-3" />{showAdvanced ? 'Masquer' : 'Options avancées'}
              </button>
              {showAdvanced && (
                <div>
                  <label className="text-xs font-medium text-slate-600 block mb-1">Negative prompt</label>
                  <input value={negativePrompt} onChange={e => setNegativePrompt(e.target.value)}
                    className="w-full text-xs border border-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-primary/30 bg-slate-50"
                    placeholder="cartoon, anime, flat, low quality…" />
                </div>
              )}

              <div className="flex gap-2">
                <button onClick={runTextTo3D}
                  disabled={!textPrompt.trim() || isRunning || apiOnline === false}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-xl text-sm font-semibold disabled:opacity-40 hover:bg-primary/90 transition-colors">
                  {step === 'converting3d' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {step === 'converting3d' ? 'Génération…' : 'Générer en 3D'}
                </button>
                <button onClick={reset} className="px-3 py-2.5 rounded-xl border border-slate-200 hover:bg-slate-50">
                  <RotateCcw className="w-4 h-4 text-slate-500" />
                </button>
              </div>
            </div>
          )}

          {/* IMAGE UPLOAD (direct / multiview / sd+tripo modes) */}
          {needsImage && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
              <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Upload className="w-4 h-4 text-primary" />
                {mode === 'sd+tripo' ? 'Image terrain / façade' : 'Photo du bâtiment'}
              </h2>
              <label className="flex flex-col items-center justify-center h-44 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:border-primary hover:bg-primary/5 transition-colors overflow-hidden">
                {inputPreview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={inputPreview} alt="input" className="h-full w-full object-contain" />
                ) : (
                  <>
                    <Upload className="w-7 h-7 text-slate-400 mb-2" />
                    <p className="text-sm text-slate-500">Cliquez pour charger une image</p>
                    <p className="text-xs text-slate-400 mt-0.5">JPG, PNG — min 512×512px recommandé</p>
                  </>
                )}
                <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
              </label>

              {/* SD prompt when in sd+tripo mode */}
              {mode === 'sd+tripo' && (
                <div>
                  <label className="text-xs font-semibold text-slate-600 flex items-center gap-1.5 mb-1">
                    <Wand2 className="w-3.5 h-3.5 text-primary" /> Prompt SD
                    <span className="font-normal text-slate-400">(optionnel)</span>
                  </label>
                  <textarea rows={2} value={sdPrompt} onChange={e => setSdPrompt(e.target.value)}
                    placeholder="modern luxury villa, Mediterranean style, white facade, professional render…"
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 bg-slate-50" />
                </div>
              )}

              <div className="flex gap-2">
                {mode === 'direct' && (
                  <button onClick={runDirect} disabled={!inputFile || isRunning || apiOnline === false}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-xl text-sm font-semibold disabled:opacity-40 hover:bg-primary/90 transition-colors">
                    {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Box className="w-4 h-4" />}
                    {isRunning ? 'Conversion…' : 'Convertir en 3D'}
                  </button>
                )}
                {mode === 'multiview' && (
                  <button onClick={runMultiview} disabled={!inputFile || isRunning || apiOnline === false}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-xl text-sm font-semibold disabled:opacity-40 hover:bg-primary/90 transition-colors">
                    {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
                    {isRunning ? 'Pipeline multiview…' : 'Générer 3D HD (multiview)'}
                  </button>
                )}
                {mode === 'sd+tripo' && (
                  <button onClick={runGenerate2D}
                    disabled={!inputFile || isRunning || apiOnline === false || sdStatus !== 'ready'}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-xl text-sm font-semibold disabled:opacity-40 hover:bg-primary/90 transition-colors">
                    {step === 'generating2d' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                    {step === 'generating2d' ? 'Génération SD…' : 'Générer Villa 2D'}
                  </button>
                )}
                <button onClick={reset} className="px-3 py-2.5 rounded-xl border border-slate-200 hover:bg-slate-50">
                  <RotateCcw className="w-4 h-4 text-slate-500" />
                </button>
              </div>

              {mode === 'multiview' && (
                <div className="flex items-start gap-2 text-[11px] text-slate-500 bg-blue-50 border border-blue-100 rounded-xl px-3 py-2">
                  <Info className="w-3.5 h-3.5 text-blue-500 mt-0.5 shrink-0" />
                  Pipeline HD : génère 4 angles (avant/gauche/arrière/droite) puis reconstruit en 3D. Prend 3–5 min.
                </div>
              )}
            </div>
          )}

          {/* 2D result (sd+tripo only) */}
          {image2d && mode === 'sd+tripo' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Villa 2D générée (SD+LoRA)</h2>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={image2d} alt="villa 2d" className="w-full rounded-xl object-contain max-h-56" />
              <button onClick={runConvert3D} disabled={step === 'converting3d' || apiOnline === false}
                className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 text-white rounded-xl text-sm font-semibold disabled:opacity-40 hover:bg-slate-700 transition-colors">
                {step === 'converting3d' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Box className="w-4 h-4" />}
                {step === 'converting3d' ? 'Tripo3D v3.1…' : 'Convertir en 3D'}
              </button>
            </div>
          )}
        </div>

        {/* ── Right: 3D viewer ──────────────────────────────────────────── */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Modèle 3D interactif</h2>

          {glbSrc ? (
            <div className="space-y-3">
              <div className="rounded-xl overflow-hidden bg-gradient-to-b from-slate-800 to-slate-950" style={{ height: 460 }}>
                <model-viewer
                  key={glbSrc}
                  src={glbSrc}
                  alt="Villa 3D"
                  auto-rotate="true"
                  camera-controls="true"
                  shadow-intensity="1.5"
                  environment-image="neutral"
                  exposure="0.9"
                  style={{ width: '100%', height: '100%', backgroundColor: 'transparent' }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                <span>Glisser pour faire pivoter · Scroll pour zoomer</span>
                {glbSize && <span>{glbSize} KB</span>}
              </div>
              <a href={glbSrc} download={glbFile || 'villa.glb'}
                className="flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-semibold hover:bg-emerald-700 transition-colors">
                <Download className="w-4 h-4" /> Télécharger le GLB ({glbFile})
              </a>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-xl bg-slate-50 border-2 border-dashed border-slate-200 gap-4 text-center px-6" style={{ height: 380 }}>
              {isRunning ? (
                <>
                  <Loader2 className="w-10 h-10 text-primary animate-spin" />
                  <div>
                    <p className="text-sm text-slate-700 font-medium">{progress}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {mode === 'multiview' ? 'Pipeline HD — environ 3 à 5 minutes' : 'Tripo3D v3.1 — environ 1 à 2 minutes'}
                    </p>
                  </div>
                  {/* progress bar placeholder */}
                  <div className="w-48 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full animate-pulse" style={{ width: '60%' }} />
                  </div>
                </>
              ) : step === 'error' ? (
                <>
                  <Box className="w-10 h-10 text-red-300" />
                  <div className="max-w-xs">
                    <p className="text-sm font-semibold text-red-700 mb-1">Erreur</p>
                    <p className="text-xs text-slate-500 break-words">
                      {errorMsg.includes('credit') || errorMsg.includes('Credit') || errorMsg.includes('2010')
                        ? 'Crédits Tripo3D insuffisants — rechargez sur tripo3d.ai'
                        : errorMsg}
                    </p>
                  </div>
                  <button onClick={reset} className="text-sm text-primary hover:underline">Réessayer</button>
                </>
              ) : (
                <>
                  <Box className="w-10 h-10 text-slate-300" />
                  <p className="text-sm text-slate-400">
                    {mode === 'text'
                      ? 'Décrivez votre modèle puis cliquez sur Générer'
                      : image2d
                      ? 'Cliquez sur « Convertir en 3D »'
                      : 'Chargez une image ou entrez un texte'}
                  </p>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Villa3DPage() {
  return <SubscriptionGuard><Villa3DContent /></SubscriptionGuard>
}
