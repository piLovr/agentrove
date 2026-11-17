// Agent Hub integration. The hub is served under the same origin at /hub/
// (see nginx-production.conf), so no auth or CORS is needed from the browser.
export const HUB_BASE: string = import.meta.env.VITE_HUB_BASE ?? '/hub';

export interface HubWindow {
  used_percent: number;
  resets_at: string | null;
}

export interface HubProvider {
  id: string;
  available: boolean;
  blocked_reason: string | null;
  windows: Record<string, HubWindow>;
}

export interface HubState {
  global_paused: boolean;
  providers: HubProvider[];
  jobs: { running: number; queued: number };
}

export interface HubChatJob {
  id: number;
  status: string;
  priority: string;
  weight: number;
  reason: string | null;
  paused: boolean;
  url: string;
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${HUB_BASE}${path}`, { credentials: 'same-origin' });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

export const fetchHubState = () => getJson<HubState>('/ui/state');

export const fetchChatJob = async (chatId: string) =>
  (await getJson<{ job: HubChatJob | null }>(`/ui/chat/${chatId}`))?.job ?? null;

export async function transcribe(audio: Blob, filename: string): Promise<string> {
  const fd = new FormData();
  fd.append('file', audio, filename);
  const r = await fetch(`${HUB_BASE}/ui/stt`, { method: 'POST', body: fd });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error ?? `HTTP ${r.status}`);
  return j.text as string;
}

export async function jobAction(jobId: number, action: 'pause' | 'resume' | 'cancel') {
  const fd = new FormData();
  fd.append('action', action);
  await fetch(`${HUB_BASE}/jobs/${jobId}/action`, { method: 'POST', body: fd, redirect: 'manual' });
}
