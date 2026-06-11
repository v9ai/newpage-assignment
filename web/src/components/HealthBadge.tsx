import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Health, ServiceStatus } from '../lib/types'

type Probe = { name: string; status: ServiceStatus }

const HEALTHY: ReadonlySet<ServiceStatus> = new Set(['ok', 'configured'])

function dotClass(status: ServiceStatus): string {
  if (HEALTHY.has(status)) return 'bg-ok'
  if (status === 'missing') return 'bg-warn'
  return 'bg-err'
}

function label(status: ServiceStatus): string {
  switch (status) {
    case 'ok':
      return 'ok'
    case 'configured':
      return 'configured'
    case 'missing':
      return 'missing'
    case 'unreachable':
      return 'unreachable'
    default:
      return 'error'
  }
}

const POLL_MS = 10000

/**
 * Live system-status panel: pings /api/health and shows a per-service ramp.
 * Distinguishes "api unreachable" (network/proxy down) from a service the api
 * itself reports as unhealthy.
 */
export function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null)
  const [reachable, setReachable] = useState(true)

  useEffect(() => {
    let cancelled = false
    let timer: number

    const poll = async () => {
      try {
        const h = await api.getHealth()
        if (cancelled) return
        setHealth(h)
        setReachable(true)
      } catch {
        if (cancelled) return
        setReachable(false)
      } finally {
        if (!cancelled) timer = window.setTimeout(poll, POLL_MS)
      }
    }

    poll()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [])

  const probes: Probe[] = reachable && health
    ? (Object.entries(health.services) as [string, ServiceStatus][]).map(
        ([name, status]) => ({ name, status }),
      )
    : (['postgres', 'qdrant', 'openai'] as const).map((name) => ({
        name,
        status: 'unreachable' as ServiceStatus,
      }))

  const allHealthy =
    reachable && probes.every((p) => HEALTHY.has(p.status))

  return (
    <section
      className="w-full rounded-card border border-border bg-surface-card/80 p-5 shadow-card backdrop-blur"
      aria-label="System status"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-wide text-ink-muted uppercase">
          System status
        </h2>
        <span className="flex items-center gap-2 text-xs text-ink-muted">
          <span
            className={`size-2 rounded-full ${
              !reachable ? 'bg-err' : allHealthy ? 'bg-ok' : 'bg-warn'
            } ${reachable ? '' : 'animate-pulse-soft'}`}
            aria-hidden="true"
          />
          {!reachable
            ? 'API unreachable'
            : allHealthy
              ? 'All systems go'
              : 'Degraded'}
          {health && reachable && (
            <span className="text-ink-faint">· v{health.version}</span>
          )}
        </span>
      </div>
      <ul className="grid gap-2 sm:grid-cols-3">
        {probes.map((p) => (
          <li
            key={p.name}
            className="flex items-center gap-2.5 rounded-lg bg-surface-sunken px-3 py-2"
          >
            <span
              className={`size-2.5 shrink-0 rounded-full ${dotClass(p.status)}`}
              aria-hidden="true"
            />
            <span className="text-sm font-medium text-ink capitalize">
              {p.name}
            </span>
            <span className="ml-auto text-xs text-ink-muted">
              {reachable ? label(p.status) : 'unreachable'}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
