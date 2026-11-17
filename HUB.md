# Agentrove: Agent Hub fork

This branch (`hub`) is upstream Agentrove plus a small set of patches for
[Agent Hub](https://github.com/pilovr/agent-hub). The upstream version it is based on is
in `HUB_UPSTREAM_VERSION`.

## Patches

New files (no conflicts with upstream):

- `frontend/src/hub/`: usage badge, mic button, hub job status line, hub page (iframe of `/hub/`).
- `backend/Dockerfile.slim`: backend image with only Claude Code, Codex and OpenCode (4.0 instead of 10.6 GB locally).
- `.github/workflows/hub-*.yml`: image build and weekly upstream sync.

Touch points in upstream files (keep these small):

- `frontend/src/App.tsx`: route `/hub`.
- `frontend/src/components/layout/TitleBar/TitleBar.tsx`: `<HubBadge />`.
- `frontend/src/components/chat/message-input/Input.tsx`: `<HubMicButton />`.
- `frontend/src/components/chat/chat-window/Chat.tsx`: `<HubJobStatus />` above the composer.
- `frontend/src/components/chat/message-bubble/Message.{tsx,module.scss}`: own messages on the right.
- `frontend/nginx-production.conf`, `frontend/Dockerfile.production`: proxy `/hub/` to the hub service (`HUB_HOST`).

## Updating

`hub-sync` runs weekly and opens a PR "Update Agentrove vX → vY" when upstream releases.
A merge conflict opens an issue listing the files. Nothing deploys by itself.

## Running

Use the compose file in the agent-hub repository. Never run this backend privileged
or with `docker.sock`: it uses host sandbox mode.
