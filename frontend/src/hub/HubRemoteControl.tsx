import { useChatQuery, useUpdateChatMutation } from '@/hooks/queries/useChatQueries';
import styles from './hub.module.scss';

/**
 * Switch for Claude Remote Control (claude.ai / desktop app) on this chat.
 * The backend resumes the chat's Claude session in an interactive
 * `claude --remote-control` process while no Agentrove turn is running.
 */
export function HubRemoteControl({ chatId }: { chatId: string | undefined }) {
  const { data: chat } = useChatQuery(chatId, { refetchInterval: 20_000 });
  const update = useUpdateChatMutation();

  if (!chatId || !chat || chat.session_agent_kind === 'codex') return null;
  const enabled = chat.remote_control !== false;

  return (
    <div className={styles.remote}>
      <label>
        <input
          type="checkbox"
          checked={enabled}
          disabled={update.isPending}
          onChange={(e) =>
            update.mutate({ chatId, updateData: { remote_control: e.target.checked } })
          }
        />
        Remote Control
      </label>
      <span className={styles.muted}>
        {!enabled
          ? 'off'
          : chat.remote_control_active
            ? 'available in claude.ai and the Claude app'
            : 'starts after the first reply'}
      </span>
    </div>
  );
}
