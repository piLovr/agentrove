import { useRef, useState } from 'react';
import { Loader2, Mic, Square } from 'lucide-react';
import toast from 'react-hot-toast';
import { transcribe } from './hubApi';
import styles from './hub.module.scss';

interface Props {
  message: string;
  setMessage: (msg: string) => void;
  disabled?: boolean;
}

/** Records audio, lets the hub transcribe it and appends the text to the input for review. */
export function HubMicButton({ message, setMessage, disabled }: Props) {
  const [state, setState] = useState<'idle' | 'rec' | 'busy'>('idle');
  const recRef = useRef<MediaRecorder | null>(null);
  const messageRef = useRef(message);
  messageRef.current = message;

  const start = async () => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      toast.error(`Microphone not available: ${(e as Error).message}`);
      return;
    }
    const type = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
    const rec = new MediaRecorder(stream, { mimeType: type });
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      setState('busy');
      try {
        const text = await transcribe(
          new Blob(chunks, { type }),
          type === 'audio/webm' ? 'voice.webm' : 'voice.m4a',
        );
        const current = messageRef.current;
        setMessage(current && !/\s$/.test(current) ? `${current} ${text}` : current + text);
      } catch (e) {
        toast.error(`Transcription failed: ${(e as Error).message}`);
      } finally {
        setState('idle');
      }
    };
    rec.start();
    recRef.current = rec;
    setState('rec');
  };

  const onClick = () => {
    if (state === 'rec') recRef.current?.stop();
    else if (state === 'idle') void start();
  };

  const Icon = state === 'rec' ? Square : state === 'busy' ? Loader2 : Mic;
  return (
    <button
      type="button"
      className={state === 'rec' ? `${styles.mic} ${styles['mic-rec']}` : styles.mic}
      onClick={onClick}
      disabled={disabled || state === 'busy'}
      aria-label={state === 'rec' ? 'Stop recording' : 'Voice input'}
      title={state === 'rec' ? 'Stop recording' : 'Voice input'}
    >
      <Icon
        className={state === 'busy' ? `${styles['mic-icon']} ${styles.spin}` : styles['mic-icon']}
      />
    </button>
  );
}
