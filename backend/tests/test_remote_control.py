import json

from app.services.remote_control import RemoteControlManager, preconfigure_home


def test_preconfigure_home_accepts_dialogs_without_clobbering(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude.json").write_text(
        json.dumps({"theme": "dark", "projects": {"/w": {"allowedTools": ["x"]}}})
    )
    preconfigure_home(str(home), "/w")
    preconfigure_home(str(home), "/other")
    cfg = json.loads((home / ".claude.json").read_text())
    assert cfg["theme"] == "dark"
    assert cfg["projects"]["/w"] == {
        "allowedTools": ["x"],
        "hasTrustDialogAccepted": True,
    }
    assert cfg["projects"]["/other"]["hasTrustDialogAccepted"] is True
    st = json.loads((home / ".claude" / "settings.json").read_text())
    assert st["skipDangerousModePermissionPrompt"] is True


async def test_manager_inactive_by_default():
    m = RemoteControlManager()
    assert m.is_active("nope") is False
    await m.stop("nope")  # no-op


async def test_start_and_stop_spawns_claude_with_resume(tmp_path, monkeypatch):
    import asyncio
    import os

    from app.services import remote_control as rc

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "claude"
    stub.write_text('#!/bin/sh\necho "ARGS: $@ HOME=$HOME"\nsleep 30\n')
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setattr(rc.settings, "STORAGE_PATH", str(tmp_path / "storage"))
    cwd = tmp_path / "ws"
    cwd.mkdir()

    m = rc.RemoteControlManager()
    await m.start(
        chat_id="c1", user_id="u1", session_id="sess-1", cwd=str(cwd), title="Hi"
    )
    assert m.is_active("c1")
    for _ in range(30):
        if "ARGS:" in m.tail("c1"):
            break
        await asyncio.sleep(0.1)
    out = m.tail("c1")
    assert (
        "--remote-control Hi --resume sess-1 --permission-mode bypassPermissions" in out
    )
    assert "agent-homes/u1" in out
    await m.stop("c1")
    assert not m.is_active("c1")
