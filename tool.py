#!/usr/bin/env python3
"""MiddAR — automated empirical-economics paper factory.

This is the CONTROL PLANE. You run it from MiddAR/; you do NOT run Claude here.
Each experiment is a sealed runtime under projects/<name>/ with its own Claude
context, config, agents, hooks, and a copied (immutable) dataset.

Layout:
    MiddAR/
      tool.py                 <- this file
      frameworks/<fw>/        <- versioned instruction-sets (edit to iterate)
      projects/<name>/        <- one sealed experiment per dir
      projects/registry.json  <- index of experiments (created on first `new`)

Commands:
    tool.py new <name> [--framework gated] [--data PATH ...] [--idea TEXT] [--force]
    tool.py list
    tool.py frameworks
    tool.py verify <name>
    tool.py clean <name> [--yes]

Examples:
    python tool.py new test_02 --data ../data --idea "Do temperature shocks affect inspection pass rates?"
    python tool.py list
    python tool.py verify test_01
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRAMEWORKS_DIR = HERE / "frameworks"
PROJECTS_DIR = HERE / "projects"
REGISTRY = PROJECTS_DIR / "registry.json"


# --- small helpers ----------------------------------------------------------
def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registry() -> dict:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text())
    return {"experiments": []}


def save_registry(reg: dict) -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2) + "\n")


def list_frameworks() -> list[str]:
    if not FRAMEWORKS_DIR.is_dir():
        return []
    return sorted(p.name for p in FRAMEWORKS_DIR.iterdir() if (p / "framework.json").exists())


def framework_meta(name: str) -> dict:
    meta_path = FRAMEWORKS_DIR / name / "framework.json"
    if not meta_path.exists():
        die(f"unknown framework {name!r}. Available: {', '.join(list_frameworks()) or '(none)'}")
    return json.loads(meta_path.read_text())


# --- commands ---------------------------------------------------------------
def cmd_frameworks(_: argparse.Namespace) -> None:
    fws = list_frameworks()
    if not fws:
        print("No frameworks found under", FRAMEWORKS_DIR)
        return
    for name in fws:
        meta = framework_meta(name)
        print(f"{name:12s} {meta.get('title', '')}")
        if meta.get("description"):
            print(f"             {meta['description']}")


def cmd_list(_: argparse.Namespace) -> None:
    reg = {e["name"]: e for e in load_registry().get("experiments", [])}
    # union registry with any project dirs on disk (e.g. created by setup.sh, pre-registry)
    on_disk = {p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()} if PROJECTS_DIR.is_dir() else set()
    names = sorted(set(reg) | on_disk)
    if not names:
        print("No experiments yet. Create one:  python tool.py new <name> --data <path>")
        return
    print(f"{'NAME':16s} {'FRAMEWORK':10s} {'CREATED':20s} STATUS")
    for name in names:
        proj = PROJECTS_DIR / name
        e = reg.get(name, {})
        fw = e.get("framework") or ("untracked" if proj.exists() else "?")
        status = "missing" if not proj.exists() else gate_status(proj)
        print(f"{name:16s} {fw:10s} {e.get('created', '-')[:19]:20s} {status}")


def gate_status(proj: Path) -> str:
    """Best-effort status from validation/report.json, else infer from disk."""
    report = proj / "validation" / "report.json"
    if report.exists():
        try:
            gates = json.loads(report.read_text()).get("gates", [])
            passed = sum(1 for g in gates if g.get("status") == "PASS")
            return f"{passed}/{len(gates)} gates PASS" if gates else "report present"
        except (json.JSONDecodeError, OSError):
            return "report unreadable"
    if (proj / "paper" / "main.tex").exists():
        return "drafting"
    return "scaffolded"


def cmd_new(args: argparse.Namespace) -> None:
    name = args.name
    if "/" in name or name in {".", ".."}:
        die("name must be a plain directory name (no slashes)")
    fw = args.framework
    meta = framework_meta(fw)
    fw_dir = FRAMEWORKS_DIR / fw

    proj = PROJECTS_DIR / name
    if proj.exists() and any(proj.iterdir()):  # an empty dir is adoptable; a populated one is not
        if not args.force:
            die(f"project {name!r} already exists and is not empty. Use --force to overwrite config (data is preserved).")
        print(f"--force: overwriting framework config in existing {name!r} (data/ preserved)")

    proj.mkdir(parents=True, exist_ok=True)

    # 1) copy framework files (CLAUDE.md, prompt.md, .claude/**) into the project.
    #    framework.json is metadata for the control plane — don't ship it into the runtime.
    for item in fw_dir.iterdir():
        if item.name == "framework.json":
            continue
        dest = proj / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    # make hooks executable
    for hook in (proj / ".claude" / "hooks").glob("*.sh"):
        hook.chmod(0o755)

    # 2) create the empty skeleton dirs the framework expects
    for rel in meta.get("skeleton_dirs", []):
        (proj / rel).mkdir(parents=True, exist_ok=True)

    # 3) copy data into the immutable data/raw/ (full isolation)
    raw = proj / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    copied = copy_data(args.data, raw)

    # 4) provenance: EXPERIMENT.md + registry entry
    write_experiment_md(proj, name, fw, args.idea, copied)
    register(name, fw, args.idea, copied)

    print(f"\nCreated experiment {name!r} (framework: {fw})")
    print(f"  data/raw/   {len(copied)} file(s) copied" if copied else "  data/raw/   EMPTY — add data before running")
    print(f"\nNext:")
    print(f"  cd {proj.relative_to(Path.cwd()) if proj.is_relative_to(Path.cwd()) else proj}")
    print(f"  claude")
    print(f"  /agents          # confirm data-profiler, econometrician, referee")
    print(f"  # then paste prompt.md as your first message")


def copy_data(data_args: list[str] | None, raw: Path) -> list[dict]:
    """Copy each --data path (file or dir) into data/raw/. Returns provenance records."""
    copied: list[dict] = []
    for src_str in data_args or []:
        src = Path(src_str).expanduser().resolve()
        if not src.exists():
            die(f"--data path not found: {src}")
        files = [f for f in src.rglob("*") if f.is_file()] if src.is_dir() else [src]
        for f in files:
            dest = raw / f.name
            shutil.copy2(f, dest)
            copied.append({"name": f.name, "source": str(f), "sha256": sha256(dest), "bytes": dest.stat().st_size})
    return copied


def write_experiment_md(proj: Path, name: str, fw: str, idea: str | None, copied: list[dict]) -> None:
    lines = [
        f"# Experiment: {name}",
        "",
        f"- **Framework:** {fw}",
        f"- **Created:** {now_iso()}",
        "",
        "## Research idea",
        "",
        (idea.strip() if idea else "_(fill this in — the orchestrator reads this file)_"),
        "",
        "## Inputs (data/raw/ — immutable)",
        "",
    ]
    if copied:
        lines += [f"- `{c['name']}` — {c['bytes']:,} bytes — sha256 `{c['sha256'][:16]}…`" for c in copied]
        lines += ["", "Sources:"]
        lines += [f"- `{c['name']}` ← `{c['source']}`" for c in copied]
    else:
        lines.append("_(none yet — add files to data/raw/ before running)_")
    lines.append("")
    (proj / "EXPERIMENT.md").write_text("\n".join(lines))


def register(name: str, fw: str, idea: str | None, copied: list[dict]) -> None:
    reg = load_registry()
    reg["experiments"] = [e for e in reg.get("experiments", []) if e.get("name") != name]
    reg["experiments"].append({
        "name": name,
        "framework": fw,
        "created": now_iso(),
        "idea": (idea or "").strip(),
        "inputs": copied,
    })
    reg["experiments"].sort(key=lambda e: e.get("created", ""))
    save_registry(reg)


def cmd_verify(args: argparse.Namespace) -> None:
    proj = PROJECTS_DIR / args.name
    runner = proj / "replication" / "run_all.sh"
    if not runner.exists():
        die(f"no replication/run_all.sh in {args.name!r} — has the pipeline run yet?")
    print(f"Running {runner.relative_to(HERE)} ...\n")
    rc = subprocess.run(["bash", str(runner)], cwd=proj).returncode
    raise SystemExit(rc)


def cmd_clean(args: argparse.Namespace) -> None:
    proj = PROJECTS_DIR / args.name
    if not proj.exists():
        die(f"no such project: {args.name!r}")
    # generated artifacts only — never the framework config or data/raw/
    targets = [
        proj / "work", proj / "paper" / "tables", proj / "paper" / "figures",
        proj / "paper" / "main.pdf", proj / "paper" / "main.aux", proj / "paper" / "main.log",
        proj / "paper" / "main.out", proj / "validation" / "report.json",
    ]
    existing = [t for t in targets if t.exists()]
    if not existing:
        print("Nothing to clean.")
        return
    print("Will delete generated artifacts (config + data/raw/ kept):")
    for t in existing:
        print(f"  {t.relative_to(proj)}")
    if not args.yes:
        if input("Proceed? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("aborted.")
            return
    for t in existing:
        shutil.rmtree(t) if t.is_dir() else t.unlink()
    print("cleaned.")


# --- arg parsing ------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tool.py", description="MiddAR experiment control plane")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="scaffold a new sealed experiment")
    n.add_argument("name")
    n.add_argument("--framework", default="gated", help="framework template (default: gated)")
    n.add_argument("--data", nargs="*", default=[], metavar="PATH", help="file(s)/dir(s) to copy into data/raw/")
    n.add_argument("--idea", default=None, help="research idea (written into EXPERIMENT.md)")
    n.add_argument("--force", action="store_true", help="overwrite config of an existing project (data preserved)")
    n.set_defaults(func=cmd_new)

    sub.add_parser("list", help="list experiments and status").set_defaults(func=cmd_list)
    sub.add_parser("frameworks", help="list available frameworks").set_defaults(func=cmd_frameworks)

    v = sub.add_parser("verify", help="run an experiment's replication/run_all.sh")
    v.add_argument("name")
    v.set_defaults(func=cmd_verify)

    c = sub.add_parser("clean", help="delete generated artifacts (keep config + data)")
    c.add_argument("name")
    c.add_argument("--yes", action="store_true", help="skip confirmation")
    c.set_defaults(func=cmd_clean)
    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
