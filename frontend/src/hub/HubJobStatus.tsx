import { useEffect, useState } from 'react';
import { fetchChatJob, jobAction, HUB_BASE, type HubChatJob } from './hubApi';
import styles from './hub.module.scss';

/** Status line above the composer for chats that the hub started as a job. */
export function HubJobStatus({ chatId }: { chatId: string | undefined }) {
  const [job, setJob] = useState<HubChatJob | null>(null);

  useEffect(() => {
    if (!chatId) return;
    let alive = true;
    const load = async () => {
      const j = await fetchChatJob(chatId);
      if (alive) setJob(j);
    };
    void load();
    const t = window.setInterval(load, 15_000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [chatId]);

  if (!job) return null;
  const act = async (a: 'pause' | 'resume' | 'cancel') => {
    await jobAction(job.id, a);
    setJob(await fetchChatJob(chatId!));
  };
  const open = !['completed', 'review', 'failed', 'cancelled'].includes(job.status);
  return (
    <div className={styles['job-status']}>
      <a href={`${HUB_BASE}/jobs/${job.id}`} className={styles['job-link']}>
        Hub job #{job.id}
      </a>
      <span className={styles.chip}>{job.status}</span>
      <span className={styles.muted}>
        {job.priority} · weight {job.weight}
        {job.reason ? ` · ${job.reason}` : ''}
      </span>
      {open && (
        <span className={styles['job-actions']}>
          {job.paused ? (
            <button type="button" onClick={() => act('resume')}>
              Resume
            </button>
          ) : (
            <button type="button" onClick={() => act('pause')}>
              Pause
            </button>
          )}
          <button type="button" onClick={() => act('cancel')}>
            Cancel
          </button>
        </span>
      )}
    </div>
  );
}
