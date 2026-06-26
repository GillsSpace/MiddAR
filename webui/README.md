# MiddAR web monitor (`webui/`)

A **read-only** web dashboard for watching MiddAR experiments. Self-contained and
zero-dependency (stdlib Python only). Everything lives under this folder — delete
`webui/` and nothing else in MiddAR is affected.

```bash
python webui/server.py            # → http://127.0.0.1:8787
python webui/server.py --port 9000 --host 0.0.0.0   # override
```

## What it does

- **Tier A — disk poll.** Left pane lists every experiment with live gate status
  (`5/8 gates PASS`, `drafting`, `ready to run`…), framework, idea, and a
  running/idle dot. Refreshes every 4s. Reuses `tool.py`'s own `load_registry` /
  `gate_status` helpers, so it can't drift from the CLI.
- **Tier B — live transcript.** Click an experiment → the right pane opens an SSE
  stream that tails that project's newest Claude Code session transcript
  (`~/.claude/projects/<encoded-path>/<session>.jsonl`) and renders each
  assistant message, tool call, and result as it lands. Backfills the last ~120
  events, then live-tails. Detects a new run (new session file) and switches to it.
  Also shows tabs for `EXPERIMENT.md` and the carry-forward `ledger.json`.

## What it deliberately does NOT do

- It never launches, kills, or signals a `claude` run — launching stays in your
  terminal exactly as `tool.py run` prints it.
- It never writes to `projects/`, the registry, or any transcript. Read-only.

So "running" in the UI just means *that project's transcript was appended to within
the last 2 minutes* — a heuristic, not a tracked process.

## Files

| File | Role |
|------|------|
| `server.py` | stdlib HTTP server: `/api/experiments`, `/api/experiment/<name>`, `/api/stream/<name>` (SSE) |
| `static/index.html` | single-page UI, no build step, no CDN |

## Possible next step (not built)

Tier C — a "Run" button that spawns `claude -p … --output-format stream-json` and
owns the process lifecycle. That adds process management + the weight of a
skip-permissions run under the server, so it was intentionally left out. The Tier B
viewer would not change when/if it's added.
