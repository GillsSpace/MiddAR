#!/usr/bin/env python3
"""MiddAR web monitor — Tier A (poll disk artifacts) + Tier B (tail session JSONL).

Self-contained, zero-dependency (stdlib only). Lives entirely under webui/ so it
can be deleted without touching the rest of MiddAR. It only READS:
  - projects/registry.json + per-project artifacts        (Tier A, via tool.py helpers)
  - ~/.claude/projects/<encoded>/<session>.jsonl          (Tier B, the live transcript)
It never launches, kills, or mutates a run.

Run:   python webui/server.py [--port 8787] [--host 127.0.0.1]
Then:  open http://127.0.0.1:8787
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                 # MiddAR/
STATIC = HERE / "static"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"

# Reuse the control-plane's own read helpers instead of duplicating them.
sys.path.insert(0, str(ROOT))
import tool  # noqa: E402  (load_registry, gate_status, framework_meta, key_names, PROJECTS_DIR)

PROJECTS_DIR: Path = tool.PROJECTS_DIR


# --------------------------------------------------------------------------- #
# Tier A — read disk artifacts into a status snapshot
# --------------------------------------------------------------------------- #
def encoded_project_dir(proj: Path) -> Path:
    """Claude Code stores a session transcript dir per cwd, with the absolute
    path encoded by replacing every non-alphanumeric char with '-'."""
    enc = re.sub(r"[^a-zA-Z0-9]", "-", str(proj.resolve()))
    return CLAUDE_PROJECTS / enc


def newest_session(proj: Path) -> Path | None:
    """Newest .jsonl transcript for a project dir (the current/last run), or None."""
    d = encoded_project_dir(proj)
    if not d.is_dir():
        return None
    sessions = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return sessions[0] if sessions else None


def experiment_snapshot(name: str, reg_entry: dict) -> dict:
    proj = PROJECTS_DIR / name
    exists = proj.exists()
    sess = newest_session(proj) if exists else None
    sess_mtime = sess.stat().st_mtime if sess else None
    now = time.time()
    # "running" is best-effort: the transcript appended to within the last 2 min.
    if sess_mtime is None:
        activity = "no-session"
    elif now - sess_mtime < 120:
        activity = "running"
    else:
        activity = "idle"
    return {
        "name": name,
        "framework": reg_entry.get("framework") or ("untracked" if exists else "?"),
        "idea": reg_entry.get("idea", ""),
        "data_mode": reg_entry.get("data_mode", ""),
        "created": (reg_entry.get("created") or "-")[:19],
        "status": tool.gate_status(proj) if exists else "missing",
        "has_paper": exists and (proj / "paper" / "main.tex").exists(),
        "has_session": sess is not None,
        "session_id": sess.stem if sess else None,
        "activity": activity,
        "last_activity": (
            datetime.fromtimestamp(sess_mtime, timezone.utc).astimezone().isoformat(timespec="seconds")
            if sess_mtime else None
        ),
    }


def list_experiments() -> list[dict]:
    reg = {e["name"]: e for e in tool.load_registry().get("experiments", [])}
    on_disk = {p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()} if PROJECTS_DIR.is_dir() else set()
    names = sorted(set(reg) | on_disk)
    return [experiment_snapshot(n, reg.get(n, {})) for n in names]


def experiment_detail(name: str) -> dict:
    proj = PROJECTS_DIR / name
    if not proj.exists():
        return {"error": f"no such project: {name}"}
    reg = {e["name"]: e for e in tool.load_registry().get("experiments", [])}
    snap = experiment_snapshot(name, reg.get(name, {}))

    def read(p: Path, limit: int = 20000) -> str | None:
        try:
            return p.read_text(errors="replace")[:limit] if p.is_file() else None
        except OSError:
            return None

    # Gate report, normalized to a list of {gate, status}.
    gates = []
    report = proj / "validation" / "report.json"
    if report.is_file():
        try:
            raw = json.loads(report.read_text()).get("gates", [])
            items = raw.items() if isinstance(raw, dict) else [(g.get("gate") or g.get("name"), g) for g in raw if isinstance(g, dict)]
            for key, g in items:
                if isinstance(g, dict):
                    gates.append({"gate": key or g.get("gate") or "?", "status": g.get("status", "?")})
        except (json.JSONDecodeError, OSError, AttributeError):
            pass

    # Ledger entries, trimmed for display.
    ledger = []
    led = proj / "ledger.json"
    if led.is_file():
        try:
            for e in json.loads(led.read_text()).get("entries", []):
                ledger.append({
                    "id": e.get("id"), "tag": e.get("tag"),
                    "artifact": (e.get("artifact") or "")[:300], "path": e.get("path"),
                })
        except (json.JSONDecodeError, OSError):
            pass

    snap.update({
        "experiment_md": read(proj / "EXPERIMENT.md"),
        "gates": gates,
        "ledger": ledger,
    })
    return snap


# --------------------------------------------------------------------------- #
# Tier B — parse one JSONL transcript line into a compact UI event
# --------------------------------------------------------------------------- #
NOISE_TYPES = {"mode", "permission-mode", "file-history-snapshot", "ai-title",
               "last-prompt", "queue-operation", "attachment"}


def _summarize_tool(name: str, inp: dict) -> str:
    if not isinstance(inp, dict):
        return ""
    for k in ("command", "file_path", "path", "pattern", "description", "prompt", "query", "url"):
        if k in inp and isinstance(inp[k], str):
            v = " ".join(inp[k].split())
            return v[:200]
    return ", ".join(f"{k}={v}" for k, v in list(inp.items())[:3])[:200]


def parse_line(raw: str) -> dict | None:
    """Turn one transcript JSONL line into {kind, ...} or None if it's noise."""
    try:
        o = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    t = o.get("type")
    if t in NOISE_TYPES:
        return None

    if t == "assistant":
        out = []
        for b in o.get("message", {}).get("content", []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and b.get("text", "").strip():
                out.append({"kind": "text", "text": b["text"].strip()})
            elif b.get("type") == "tool_use":
                out.append({"kind": "tool", "tool": b.get("name", "?"),
                            "summary": _summarize_tool(b.get("name", ""), b.get("input", {}))})
        # collapse a multi-block turn into the first meaningful event (rest streamed too)
        return {"kind": "group", "events": out} if out else None

    if t == "user":
        content = o.get("message", {}).get("content")
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    if isinstance(c, list):
                        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    return {"kind": "result", "text": (str(c) or "").strip()[:400]}
        elif isinstance(content, str) and content.strip():
            return {"kind": "user", "text": content.strip()[:400]}
        return None

    if t == "system":
        msg = o.get("content") or o.get("message") or ""
        return {"kind": "system", "text": str(msg)[:300]}

    return None


def flatten(parsed: dict | None) -> list[dict]:
    if parsed is None:
        return []
    if parsed.get("kind") == "group":
        return parsed["events"]
    return [parsed]


def sse(handler: BaseHTTPRequestHandler, name: str) -> None:
    """Stream a project's newest transcript as Server-Sent Events.
    Sends the tail of existing events first, then live-tails appended lines."""
    proj = PROJECTS_DIR / name
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()

    def emit(ev: dict) -> bool:
        try:
            handler.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
            handler.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, ValueError):
            return False

    sess = newest_session(proj)
    if sess is None:
        emit({"kind": "system", "text": "no session transcript yet — waiting for a run to start…"})
    pos = 0
    # Backfill: stream the last slice of the file so the panel isn't empty.
    if sess and sess.is_file():
        lines = sess.read_text(errors="replace").splitlines()
        for ln in lines[-120:]:
            for ev in flatten(parse_line(ln)):
                if not emit(ev):
                    return
        pos = sess.stat().st_size

    last_ping = time.time()
    while True:
        # A new run = a newer session file appears; switch to it.
        newest = newest_session(proj)
        if newest and newest != sess:
            sess, pos = newest, 0
            emit({"kind": "system", "text": f"new session: {sess.stem}"})
        if sess and sess.is_file():
            size = sess.stat().st_size
            if size > pos:
                with sess.open("r", errors="replace") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                # only process complete lines; stash a trailing partial by rewinding
                if not chunk.endswith("\n") and "\n" in chunk:
                    keep = chunk.rsplit("\n", 1)[1]
                    pos -= len(keep.encode())
                    chunk = chunk[: len(chunk) - len(keep)]
                for ln in chunk.splitlines():
                    for ev in flatten(parse_line(ln)):
                        if not emit(ev):
                            return
        if time.time() - last_ping > 15:
            last_ping = time.time()
            try:
                handler.wfile.write(b": ping\n\n")
                handler.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ValueError):
                return
        time.sleep(0.6)


# --------------------------------------------------------------------------- #
# HTTP routing
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # close-delimited bodies keep SSE simple & robust

    def log_message(self, *_):  # quiet
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, ctype: str):
        if not path.is_file():
            self._json({"error": "not found"}, 404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path).path
        try:
            if route in ("/", "/index.html"):
                self._file(STATIC / "index.html", "text/html; charset=utf-8")
            elif route == "/api/experiments":
                self._json(list_experiments())
            elif route.startswith("/api/experiment/"):
                self._json(experiment_detail(unquote(route.rsplit("/", 1)[1])))
            elif route.startswith("/api/stream/"):
                sse(self, unquote(route.rsplit("/", 1)[1]))
            else:
                self._json({"error": "not found"}, 404)
        except BrokenPipeError:
            pass
        except Exception as e:  # never let one bad request kill the thread
            try:
                self._json({"error": repr(e)}, 500)
            except OSError:
                pass


def main():
    ap = argparse.ArgumentParser(description="MiddAR web monitor (read-only).")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    print(f"MiddAR monitor → http://{args.host}:{args.port}  (Ctrl-C to stop)")
    print(f"  reading projects from: {PROJECTS_DIR}")
    print(f"  reading transcripts from: {CLAUDE_PROJECTS}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
