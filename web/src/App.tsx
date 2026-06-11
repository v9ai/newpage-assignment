import { useEffect, useState } from 'react'

type ServiceStatus = 'ok' | 'error' | 'configured' | 'missing' | 'unreachable'

interface Health {
  ok: boolean
  version: string
  services: {
    postgres: ServiceStatus
    qdrant: ServiceStatus
    openai: ServiceStatus
  }
}

function StatusDot({ status }: { status: ServiceStatus }) {
  const healthy = status === 'ok' || status === 'configured'
  return (
    <span
      className={`inline-block size-2.5 rounded-full ${healthy ? 'bg-ok' : 'bg-err'}`}
      aria-label={healthy ? 'healthy' : 'unhealthy'}
    />
  )
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [unreachable, setUnreachable] = useState(false)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json() as Promise<Health>)
      .then(setHealth)
      .catch(() => setUnreachable(true))
  }, [])

  const services: [string, ServiceStatus][] = health
    ? (Object.entries(health.services) as [string, ServiceStatus][])
    : [
        ['postgres', 'unreachable'],
        ['qdrant', 'unreachable'],
        ['openai', 'unreachable'],
      ]

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-10 px-6">
      <header className="text-center">
        <h1 className="text-5xl font-bold tracking-tight">
          Doc<span className="text-accent">Chat</span>
        </h1>
        <p className="mt-3 text-lg text-ink-muted">
          Ask questions about your documents. Get answers with citations.
        </p>
      </header>

      <section className="w-full rounded-2xl border border-accent-soft bg-surface-card p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-ink-muted">
          System status {health && <span className="font-normal">· v{health.version}</span>}
        </h2>
        <ul className="space-y-2">
          {services.map(([name, status]) => (
            <li key={name} className="flex items-center gap-3">
              <StatusDot status={status} />
              <span className="capitalize">{name}</span>
              <span className="ml-auto text-sm text-ink-muted">
                {unreachable ? 'api unreachable' : status}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <button
        disabled
        className="cursor-not-allowed rounded-xl bg-accent px-6 py-3 font-medium text-white opacity-40"
        title="Document upload arrives in Phase 2"
      >
        Upload documents — coming soon
      </button>
    </main>
  )
}
