import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { HUB_BASE } from './hubApi';
import styles from './hub.module.scss';

/** The hub's own GUI (queue, limits, providers, projects, plugins, settings) as a tab. */
export function HubPage() {
  const navigate = useNavigate();
  return (
    <div className={styles.page}>
      <div className={styles['page-bar']}>
        <button type="button" onClick={() => navigate('/')} className={styles.back}>
          <ArrowLeft className={styles['mic-icon']} /> Agentrove
        </button>
        <span className={styles.muted}>Agent Hub</span>
        <a href={`${HUB_BASE}/`} target="_blank" rel="noreferrer" className={styles.muted}>
          ↗
        </a>
      </div>
      <iframe title="Agent Hub" src={`${HUB_BASE}/`} className={styles.frame} allow="microphone" />
    </div>
  );
}
