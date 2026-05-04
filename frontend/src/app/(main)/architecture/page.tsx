import Link from 'next/link'
import {
  ArrowRight,
  BarChart3,
  Brain,
  Calculator,
  Code2,
  MapPin,
  MessageSquare,
  Network,
  Scale,
  Search,
  Server,
  Sparkles,
} from 'lucide-react'

const flow = [
  { title: 'Frontend Next.js', detail: 'Pages web et formulaires utilisés pendant la démo' },
  { title: 'Orchestrateur :8000', detail: "Couche d'orchestration appelée par le frontend" },
  { title: 'Routes API', detail: '/search, /chat, /forecast, /dhia/predict, /dhia/invest...' },
  { title: 'Service Dhia :8055', detail: 'Microservice ML + génération de rapports' },
  { title: 'Gemini / Data', detail: 'Narration IA et données exploitées par les agents' },
]

const touchpoints = [
  {
    title: 'Base commune API',
    file: 'frontend/src/lib/api.ts',
    icon: Code2,
    routes: 'NEXT_PUBLIC_ORCHESTRATOR_URL, /chat, /search, /listings, /dhia/predict, /dhia/invest',
    desc: "Toutes les fonctions frontend qui appellent l'orchestrateur passent par ce fichier.",
  },
  {
    title: 'Recherche immobilière',
    file: 'frontend/src/app/(main)/search/page.tsx',
    icon: Search,
    routes: '/search et /listings',
    desc: 'Affiche les annonces enrichies par les agents et ouvre la fiche détaillée.',
  },
  {
    title: 'Conseiller IA',
    file: 'frontend/src/app/(main)/advisor/page.tsx',
    icon: MessageSquare,
    routes: '/advisor/prompt',
    desc: "Envoie la demande utilisateur à l'orchestrateur pour une réponse conversationnelle.",
  },
  {
    title: 'Agents Dhia',
    file: 'frontend/src/app/(main)/predict/page.tsx',
    icon: Brain,
    routes: '/dhia/predict et /dhia/invest',
    desc: "Montre l'agent de prédiction de prix et l'agent d'investissement.",
  },
  {
    title: "Fiche d'un bien",
    file: 'frontend/src/app/(main)/listing/[id]/page.tsx',
    icon: Sparkles,
    routes: '/listing/:id, /dhia/predict, /dhia/invest',
    desc: "Combine les infos du bien avec les analyses Dhia dans l'onglet Analyse IA.",
  },
  {
    title: 'Prévision du marché',
    file: 'frontend/src/app/(main)/forecast/page.tsx',
    icon: BarChart3,
    routes: '/forecast/:governorat et /market/summary',
    desc: "Explique l'évolution du marché par gouvernorat via l'orchestrateur.",
  },
  {
    title: 'Devis travaux',
    file: 'frontend/src/app/(main)/devis/page.tsx',
    icon: Calculator,
    routes: '/chat',
    desc: "Passe par l'orchestrateur pour produire l'estimation de travaux.",
  },
  {
    title: 'Juridique immobilier',
    file: 'frontend/src/app/(main)/legal/page.tsx',
    icon: Scale,
    routes: '/chat',
    desc: "Interroge l'orchestrateur pour les réponses réglementaires et contractuelles.",
  },
  {
    title: 'Lifestyle / quartier',
    file: 'frontend/src/app/(main)/lifestyle/page.tsx',
    icon: MapPin,
    routes: "API lifestyle via l'orchestrateur",
    desc: "Aide à expliquer la valeur d'un quartier et le profil de vie associé.",
  },
]

const demoSteps = [
  'Ouvrir "Agents IA" dans la barre de navigation pour montrer la prédiction de prix et le scoring investissement.',
  'Lancer un exemple sur Tunis ou Sousse avec "Lancer les deux agents".',
  "Montrer cette page pour expliquer que le frontend appelle l'orchestrateur sur le port 8000.",
  "Finir sur la fiche d'un bien pour prouver que les mêmes agents sont réutilisés dans le parcours réel utilisateur.",
]

export default function ArchitecturePage() {
  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-primary-50 px-3 py-1 text-sm font-semibold text-primary">
              <Network className="h-4 w-4" />
              Architecture technique
            </div>
            <h1 className="text-3xl font-bold text-slate-900">Architecture des agents IA</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              L'orchestrateur coordonne le frontend, les services d'analyse et les agents Dhia.
              Cette page résume exactement quoi montrer pendant la soutenance.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/predict"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-600"
            >
              <Brain className="h-4 w-4" />
              Ouvrir les agents IA
            </Link>
            <Link
              href="/search"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-100"
            >
              <Search className="h-4 w-4" />
              Ouvrir le parcours réel
            </Link>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Server className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold text-slate-800">Flux global</h2>
        </div>
        <div className="flex flex-wrap gap-3 text-sm text-slate-700">
          {flow.map((item, index) => (
            <div key={item.title} className="flex items-center gap-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="font-semibold text-slate-800">{item.title}</p>
                <p className="mt-1 max-w-[220px] text-xs text-slate-500">{item.detail}</p>
              </div>
              {index < flow.length - 1 && <ArrowRight className="h-4 w-4 text-slate-400" />}
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {touchpoints.map(({ title, file, icon: Icon, routes, desc }) => (
          <div key={title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <div className="rounded-xl bg-primary-50 p-2 text-primary">
                <Icon className="h-4 w-4" />
              </div>
              <h3 className="font-semibold text-slate-800">{title}</h3>
            </div>
            <p className="mb-2 text-xs font-medium text-slate-500">{file}</p>
            <p className="mb-3 text-sm leading-6 text-slate-600">{desc}</p>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Routes</p>
              <p className="mt-1 font-mono text-xs text-slate-700">{routes}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="rounded-3xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">Comment le présenter au professeur</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {demoSteps.map((step, index) => (
            <div key={index} className="rounded-2xl border border-emerald-200 bg-white p-4">
              <p className="mb-2 text-xs font-bold text-emerald-700">Étape {index + 1}</p>
              <p className="text-sm text-slate-700">{step}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
