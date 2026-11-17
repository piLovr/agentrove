import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Gauge } from 'lucide-react';
import { fetchHubState, type HubState } from './hubApi';
import styles from './hub.module.scss';

const LABELS: Record<string, string> = { '5h': '5h', week: 'W' };

function level(pct: number) {
  if (pct >= 90) return styles.bad;
  if (pct >= 70) return styles.warn;
  return styles.ok;
}

/** Subscription usage (5h / week per provider) in the title bar; click opens the hub. */
export function HubBadge() {
  const navigate = useNavigate();
  const [state, setState] = useState<HubState | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      const s = await fetchHubState();
      if (alive) setState(s);
    };
    void load();
    const t = window.setInterval(load, 30_000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, []);

  if (!state) return null;
  return (
    <button
      type="button"
      className={styles.badge}
      onClick={() => navigate('/hub')}
      title="Agent Hub: limits and jobs"
    >
      <Gauge className={styles['badge-icon']} />
      {state.global_paused && <span className={styles.bad}>paused</span>}
      {state.providers.map((p) => (
        <span key={p.id} className={styles['badge-provider']} title={p.blocked_reason ?? ''}>
          <span className={p.available ? undefined : styles.bad}>{p.id}</span>
          {Object.entries(p.windows).map(([name, w]) => (
            <span key={name} className={level(w.used_percent)}>
              {LABELS[name] ?? name} {Math.round(w.used_percent)}%
            </span>
          ))}
        </span>
      ))}
      {(state.jobs.running > 0 || state.jobs.queued > 0) && (
        <span className={styles.muted}>
          ▶ {state.jobs.running} · ⏳ {state.jobs.queued}
        </span>
      )}
    </button>
  );
}
