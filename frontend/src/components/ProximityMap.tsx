/**
 * ProximityMap.tsx
 * Mini-carte Leaflet centrée sur le bien avec :
 *  - Cercle de rayon 500 m
 *  - Détection des services via Overpass API (gratuit, sans clé)
 *  - Markers colorés par catégorie
 *  - Callback onServicesDetected(string[]) vers le formulaire parent
 */

import { useEffect, useRef, useState, useCallback } from "react";
import type { Map as LeafletMap, CircleMarker } from "leaflet";

// ── Constantes ────────────────────────────────────────────────────────────────

const RADIUS_M = 500;

const SERVICE_CONFIG: Record<string, { label: string; color: string; coeff: number }> = {
  supermarche: { label: "Supermarché / Épicerie", color: "#10b981", coeff: 3 },
  pharmacie:   { label: "Pharmacie",              color: "#3b82f6", coeff: 2 },
  ecole:       { label: "École / Lycée",           color: "#8b5cf6", coeff: 4 },
  transport:   { label: "Transport en commun",     color: "#f59e0b", coeff: 5 },
  restaurant:  { label: "Café / Restaurant",       color: "#ec4899", coeff: 1 },
  hopital:     { label: "Hôpital / Clinique",      color: "#ef4444", coeff: 3 },
  mosquee:     { label: "Mosquée",                 color: "#6366f1", coeff: 1 },
  parc:        { label: "Parc / Espace vert",      color: "#22c55e", coeff: 3 },
};

// Mapping des tags Overpass → clés internes
function classifyNode(tags: Record<string, string>): string | null {
  const { amenity, shop, highway, railway, leisure, religion } = tags;
  if (shop && ["supermarket", "convenience", "grocery", "bakery"].includes(shop)) return "supermarche";
  if (amenity === "pharmacy" || amenity === "chemist") return "pharmacie";
  if (amenity && ["school", "college", "university", "kindergarten"].includes(amenity)) return "ecole";
  if (highway === "bus_stop" || (railway && ["station", "halt", "tram_stop", "subway_entrance"].includes(railway))) return "transport";
  if (amenity && ["restaurant", "cafe", "fast_food", "bar"].includes(amenity)) return "restaurant";
  if (amenity && ["hospital", "clinic", "doctors", "dentist"].includes(amenity)) return "hopital";
  if (amenity === "place_of_worship" && religion === "muslim") return "mosquee";
  if (leisure && ["park", "garden", "playground"].includes(leisure)) return "parc";
  return null;
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface DetectedService {
  type: string;
  name: string;
  lat: number;
  lng: number;
}

interface Props {
  lat: number;
  lng: number;
  ville: string;
  onServicesDetected: (services: string[]) => void;
}

// ── Composant ─────────────────────────────────────────────────────────────────

export default function ProximityMap({ lat, lng, ville, onServicesDetected }: Props) {
  const mapDivRef = useRef<HTMLDivElement>(null);
  const mapRef    = useRef<LeafletMap | null>(null);
  const markersRef = useRef<CircleMarker[]>([]);

  const [detected, setDetected]     = useState<DetectedService[]>([]);
  const [loading, setLoading]        = useState(false);
  const [error, setError]            = useState<string | null>(null);
  const [scoreTotal, setScoreTotal]  = useState(0);

  // ── Leaflet initialisation (une seule fois) ───────────────────────────────
  useEffect(() => {
    if (!mapDivRef.current || mapRef.current) return;

    import("leaflet").then((L) => {
      // Fix icônes par défaut dans Vite
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      const map = L.map(mapDivRef.current!, { zoomControl: true, scrollWheelZoom: false });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 18,
      }).addTo(map);

      mapRef.current = map;
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Mise à jour centre + cercle + requête Overpass à chaque lat/lng ────────
  const runQuery = useCallback(async () => {
    const L = (await import("leaflet")).default;
    const map = mapRef.current;
    if (!map) return;

    setLoading(true);
    setError(null);

    // Centrer la carte
    map.setView([lat, lng], 15);

    // Supprimer anciens markers et cercle
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
    map.eachLayer((layer) => {
      if ((layer as { _isProximityCircle?: boolean })._isProximityCircle) {
        map.removeLayer(layer);
      }
    });

    // Marker principal (bien)
    const homeIcon = L.divIcon({
      html: `<div style="background:#2563eb;width:14px;height:14px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4)"></div>`,
      iconSize: [14, 14], iconAnchor: [7, 7], className: "",
    });
    L.marker([lat, lng], { icon: homeIcon }).addTo(map).bindPopup(`<b>${ville || "Bien"}</b>`);

    // Cercle 500 m
    const circle = L.circle([lat, lng], {
      radius: RADIUS_M,
      color: "#2563eb",
      fillColor: "#2563eb",
      fillOpacity: 0.05,
      weight: 1.5,
      dashArray: "6 4",
    }).addTo(map);
    (circle as unknown as { _isProximityCircle: boolean })._isProximityCircle = true;

    // ── Requête Overpass ────────────────────────────────────────────────────
    const query = `
[out:json][timeout:15];
(
  node["shop"~"supermarket|convenience|grocery|bakery"](around:${RADIUS_M},${lat},${lng});
  node["amenity"~"pharmacy|chemist"](around:${RADIUS_M},${lat},${lng});
  node["amenity"~"school|college|university|kindergarten"](around:${RADIUS_M},${lat},${lng});
  node["highway"="bus_stop"](around:${RADIUS_M},${lat},${lng});
  node["railway"~"station|halt|tram_stop|subway_entrance"](around:${RADIUS_M},${lat},${lng});
  node["amenity"~"restaurant|cafe|fast_food|bar"](around:${RADIUS_M},${lat},${lng});
  node["amenity"~"hospital|clinic|doctors|dentist"](around:${RADIUS_M},${lat},${lng});
  node["amenity"="place_of_worship"]["religion"="muslim"](around:${RADIUS_M},${lat},${lng});
  node["leisure"~"park|garden|playground"](around:${RADIUS_M},${lat},${lng});
);
out body;`;

    try {
      const res = await fetch(
        `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`,
        { signal: AbortSignal.timeout(18_000) }
      );
      if (!res.ok) throw new Error(`Overpass API ${res.status}`);
      const json = await res.json();

      const found: DetectedService[] = [];
      const seenTypes = new Set<string>();

      for (const node of json.elements ?? []) {
        const type = classifyNode(node.tags ?? {});
        if (!type) continue;
        const name = node.tags?.name ?? SERVICE_CONFIG[type]?.label ?? type;
        found.push({ type, name, lat: node.lat, lng: node.lon });

        // Marker coloré
        const cfg = SERVICE_CONFIG[type];
        const icon = L.divIcon({
          html: `<div title="${name}" style="background:${cfg.color};width:10px;height:10px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.3)"></div>`,
          iconSize: [10, 10], iconAnchor: [5, 5], className: "",
        });
        const marker = L.marker([node.lat, node.lon], { icon })
          .addTo(map)
          .bindPopup(`<b>${name}</b><br><span style="color:${cfg.color}">${cfg.label}</span>`);
        markersRef.current.push(marker as unknown as CircleMarker);

        seenTypes.add(type);
      }

      setDetected(found);

      const uniqueTypes = [...seenTypes];
      const score = uniqueTypes.reduce((s, t) => s + (SERVICE_CONFIG[t]?.coeff ?? 0), 0);
      setScoreTotal(score);
      onServicesDetected(uniqueTypes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur réseau";
      setError(`Impossible de charger les services de proximité (${msg})`);
      onServicesDetected([]);
    } finally {
      setLoading(false);
    }
  }, [lat, lng, ville, onServicesDetected]);

  useEffect(() => {
    // Attendre que la map soit initialisée
    const timer = setTimeout(runQuery, 300);
    return () => clearTimeout(timer);
  }, [runQuery]);

  // ── Grouper par type ──────────────────────────────────────────────────────
  const grouped = detected.reduce<Record<string, DetectedService[]>>((acc, s) => {
    (acc[s.type] ??= []).push(s);
    return acc;
  }, {});

  const uniqueTypes = Object.keys(grouped);
  const totalCoeff  = uniqueTypes.reduce((s, t) => s + (SERVICE_CONFIG[t]?.coeff ?? 0), 0);

  return (
    <div className="space-y-3">
      {/* Carte */}
      <div className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm">
        {/* Import CSS Leaflet */}
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          crossOrigin=""
        />
        <div ref={mapDivRef} style={{ height: 260 }} />

        {loading && (
          <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-[9999]">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              Détection des services…
            </div>
          </div>
        )}
      </div>

      {/* Légende */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <span>Rayon d'analyse : <strong>500 m</strong></span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-600 inline-block" />
          Centre du bien
        </span>
      </div>

      {/* Erreur */}
      {error && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      {/* Services détectés */}
      {!loading && uniqueTypes.length > 0 && (
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-700">
              Services détectés ({detected.length} établissements)
            </p>
            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
              Score +{(totalCoeff / 100).toFixed(0)}%
            </span>
          </div>
          <div className="grid grid-cols-1 gap-1.5">
            {uniqueTypes.map((type) => {
              const cfg = SERVICE_CONFIG[type];
              const count = grouped[type].length;
              return (
                <div key={type} className="flex items-center gap-2 text-xs">
                  <span
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ background: cfg.color }}
                  />
                  <span className="text-slate-600 flex-1">{cfg.label}</span>
                  <span className="text-slate-400">{count}×</span>
                  <span className="font-semibold text-emerald-600">+{cfg.coeff}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!loading && uniqueTypes.length === 0 && !error && (
        <p className="text-xs text-slate-400 text-center py-1">
          Aucun service détecté dans un rayon de 500 m.{" "}
          <span className="text-slate-500">(Score proximité : 0%)</span>
        </p>
      )}

      {/* Score synthèse */}
      {!loading && uniqueTypes.length > 0 && (
        <div className="text-xs text-slate-500 text-center">
          Score de proximité cumulé :{" "}
          <strong className="text-emerald-600">+{scoreTotal}%</strong>{" "}
          appliqué sur le prix de référence
        </div>
      )}
    </div>
  );
}
