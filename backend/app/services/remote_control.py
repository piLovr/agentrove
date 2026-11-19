"""Hub fork: expose Claude chats through Claude Code Remote Control.

Remote Control only exists for *interactive* `claude` sessions (headless/ACP
ignores `--remote-control`), so for each enabled chat we resume the chat's
Claude session in an interactive `claude --remote-control` process on a pty.
That makes the session visible in claude.ai and the desktop app.

Only one process may drive a transcript at a time, so the process is stopped
while an Agentrove turn runs and restarted afterwards.

The two start-up dialogs (folder trust, bypass-permissions warning) are
answered up front through the agent HOME's config, never by sending keystrokes.
"""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import json
import logging
import os
import pty
import signal
import struct
import subprocess
import termios
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.db_models.chat import Chat

logger = logging.getLogger(__name__)
settings = get_settings()

TAIL_BYTES = 4000


@dataclass
class _Proc:
    popen: subprocess.Popen[bytes]
    master_fd: int
    started_at: float = field(default_factory=time.monotonic)
    tail: bytes = b""


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def preconfigure_home(home: str, cwd: str) -> None:
    """Accept the folder-trust and bypass-permissions dialogs in config.

    Agentrove already runs every Claude turn in bypassPermissions inside its
    unprivileged host sandbox; this records that acceptance for the interactive
    process too.
    """
    home_path = Path(home)
    cfg_path = home_path / ".claude.json"
    cfg = _read_json(cfg_path)
    project = cfg.setdefault("projects", {}).setdefault(cwd, {})
    changed = not project.get("hasTrustDialogAccepted")
    project["hasTrustDialogAccepted"] = True
    if changed:
        _write_json(cfg_path, cfg)
    settings_path = home_path / ".claude" / "settings.json"
    st = _read_json(settings_path)
    if st.get("skipDangerousModePermissionPrompt") is not True:
        st["skipDangerousModePermissionPrompt"] = True
        _write_json(settings_path, st)


class RemoteControlManager:
    def __init__(self) -> None:
        self._procs: dict[str, _Proc] = {}
        self._lock_obj: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None

    @property
    def _lock(self) -> asyncio.Lock:
        # Rebuilt if the running loop changed (tests run one loop per test).
        loop = asyncio.get_running_loop()
        if self._lock_obj is None or self._lock_loop is not loop:
            self._lock_obj, self._lock_loop = asyncio.Lock(), loop
        return self._lock_obj

    def is_active(self, chat_id: str) -> bool:
        p = self._procs.get(chat_id)
        return p is not None and p.popen.poll() is None

    def tail(self, chat_id: str) -> str:
        p = self._procs.get(chat_id)
        return p.tail.decode(errors="ignore") if p else ""

    def _drain(self, chat_id: str, proc: _Proc) -> None:
        try:
            data = os.read(proc.master_fd, 65536)
        except OSError:
            data = b""
        if not data:
            asyncio.get_running_loop().remove_reader(proc.master_fd)
            return
        proc.tail = (proc.tail + data)[-TAIL_BYTES:]

    async def start(
        self,
        *,
        chat_id: str,
        user_id: str,
        session_id: str,
        cwd: str,
        title: str,
    ) -> None:
        async with self._lock:
            if self.is_active(chat_id):
                return
            self._reap(chat_id)
            # Keep the number of idle node processes bounded: evict the oldest.
            while len(self._procs) >= settings.REMOTE_CONTROL_MAX_PROCESSES:
                oldest = min(self._procs, key=lambda k: self._procs[k].started_at)
                await self._stop_locked(oldest)
            home = settings.get_agent_home_dir(user_id)
            preconfigure_home(home, cwd)
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))
            env = {
                **os.environ,
                "HOME": home,
                "TERM": "xterm-256color",
                "IS_SANDBOX": "1",
            }
            try:
                popen = subprocess.Popen(  # noqa: S603
                    [
                        "claude",
                        "--remote-control",
                        title[:80] or "Agentrove chat",
                        "--resume",
                        session_id,
                        "--permission-mode",
                        "bypassPermissions",
                    ],
                    cwd=cwd,
                    stdin=slave,
                    stdout=slave,
                    stderr=slave,
                    start_new_session=True,
                    env=env,
                )
            except OSError as exc:
                logger.warning("remote control start failed for %s: %s", chat_id, exc)
                os.close(master)
                return
            finally:
                os.close(slave)
            proc = _Proc(popen=popen, master_fd=master)
            self._procs[chat_id] = proc
            asyncio.get_running_loop().add_reader(master, self._drain, chat_id, proc)
            logger.info("remote control started chat=%s pid=%s", chat_id, popen.pid)

    def _reap(self, chat_id: str) -> None:
        proc = self._procs.pop(chat_id, None)
        if proc is None:
            return
        with contextlib.suppress(Exception):
            asyncio.get_running_loop().remove_reader(proc.master_fd)
        with contextlib.suppress(OSError):
            os.close(proc.master_fd)

    async def _stop_locked(self, chat_id: str) -> None:
        proc = self._procs.get(chat_id)
        if proc is None:
            return
        if proc.popen.poll() is None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(proc.popen.pid, signal.SIGTERM)
            for _ in range(30):
                if proc.popen.poll() is not None:
                    break
                await asyncio.sleep(0.1)
            else:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(proc.popen.pid, signal.SIGKILL)
            with contextlib.suppress(Exception):
                proc.popen.wait(timeout=2)
        self._reap(chat_id)
        logger.info("remote control stopped chat=%s", chat_id)

    async def stop(self, chat_id: str) -> None:
        async with self._lock:
            await self._stop_locked(chat_id)

    async def stop_all(self) -> None:
        async with self._lock:
            for chat_id in list(self._procs):
                await self._stop_locked(chat_id)

    async def sync(self, chat_id: str, session_factory) -> None:  # type: ignore[no-untyped-def]
        """Start or stop the chat's process to match its current DB state."""
        if not settings.REMOTE_CONTROL_ENABLED:
            return
        async with session_factory() as db:
            result = await db.execute(
                select(Chat)
                .options(selectinload(Chat.workspace))
                .filter(Chat.id == UUID(chat_id))
            )
            chat = result.scalar_one_or_none()
        if (
            chat is None
            or chat.deleted_at is not None
            or not chat.remote_control
            or not chat.session_id
            or chat.session_agent_kind not in (None, "claude")
            or chat.workspace is None
            or chat.workspace.sandbox_provider != "host"
        ):
            await self.stop(chat_id)
            return
        cwd = chat.worktree_cwd or chat.workspace.workspace_path
        if not cwd or not Path(cwd).is_dir():
            await self.stop(chat_id)
            return
        await self.start(
            chat_id=chat_id,
            user_id=str(chat.user_id),
            session_id=chat.session_id,
            cwd=cwd,
            title=chat.title,
        )


remote_control = RemoteControlManager()
