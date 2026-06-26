#!/usr/bin/env python3
"""MiddAR — automated empirical-economics paper factory.

This is the CONTROL PLANE. You run it from MiddAR/; you do NOT run Claude here.
Each experiment is a sealed runtime under projects/<name>/ with its own Claude
context, config, agents, hooks, and its own dataset in data/raw/.

Two main commands:
    gen <name> [--framework gated] [--idea TEXT]
        Generate the project folder structure from a framework.
        Leaves data/raw/ EMPTY — you copy this experiment's dataset in next.

    run <name>
        Finish setup (verify data is present, hash it, finalize provenance) and
        print the command + prompt to paste into Claude Code to start working.

Typical flow:
    python tool.py gen exp_03 --framework gated --idea "Does X affect Y?"
    cp /path/to/your_dataset.parquet projects/exp_03/data/raw/
    python tool.py run exp_03

Helpers:
    python tool.py list          # experiments + status
    python tool.py frameworks    # available frameworks
    python tool.py verify <name> # re-run replication/run_all.sh
    python tool.py clean <name>  # delete generated artifacts (keep config + data)

Layout:
    MiddAR/
      tool.py                 <- this file
      frameworks/<fw>/        <- versioned instruction-sets (edit to iterate)
      projects/<name>/        <- one sealed experiment per dir
      projects/registry.json  <- index of experiments
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
API_KEYS_MASTER = HERE / "api_keys.env"  # single user-editable master; copied into each project

API_KEYS_TEMPLATE = """\
# MiddAR API keys — master file (control plane).
# Edit this ONE file; `tool.py gen`/`run` copies it into each project so the
# sealed-context model can read keys it needs for API data pulls.
#
# Format: KEY=VALUE, one per line. Lines starting with # are ignored.
# The framework instructs the model to READ these and NEVER print, log, or
# commit a key value. Leave a line blank/absent if you don't have that key.
#
# Keep this file out of version control (add `api_keys.env` to .gitignore).

# Recommended easy-to-get keys (all free, instant/near-instant signup):
# CENSUS_API_KEY=        # api.census.gov/data/key_signup.html  — ACS/Decennial/CBP
# FRED_API_KEY=          # fredaccount.stlouisfed.org/apikeys   — macro/financial/regional series
# BLS_API_KEY=           # data.bls.gov/registrationEngine      — CPI, employment, wages, JOLTS
# BEA_API_KEY=           # apps.bea.gov/API/signup              — GDP, national/regional accounts
# EIA_API_KEY=           # eia.gov/opendata/register.php        — energy prices/production/consumption
# NOAA_CDO_TOKEN=        # ncdc.noaa.gov/cdo-web/token          — historical weather (identification pairings)
# DATA_GOV_API_KEY=      # api.data.gov/signup                  — umbrella key for many federal APIs
"""


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


def upsert_experiment(name: str, **fields) -> None:
    reg = load_registry()
    exps = [e for e in reg.get("experiments", []) if e.get("name") != name]
    existing = next((e for e in reg.get("experiments", []) if e.get("name") == name), {})
    existing.update(name=name, **fields)
    exps.append(existing)
    exps.sort(key=lambda e: e.get("created", ""))
    reg["experiments"] = exps
    save_registry(reg)


def list_frameworks() -> list[str]:
    if not FRAMEWORKS_DIR.is_dir():
        return []
    return sorted(p.name for p in FRAMEWORKS_DIR.iterdir() if (p / "framework.json").exists())


def framework_meta(name: str) -> dict:
    meta_path = FRAMEWORKS_DIR / name / "framework.json"
    if not meta_path.exists():
        die(f"unknown framework {name!r}. Available: {', '.join(list_frameworks()) or '(none)'}")
    return json.loads(meta_path.read_text())


def scan_raw(proj: Path) -> list[dict]:
    """Provenance records for whatever is currently in data/raw/ (excludes seal files)."""
    raw = proj / "data" / "raw"
    files = sorted(f for f in raw.rglob("*") if f.is_file() and f.name != ".sealed") if raw.is_dir() else []
    return [{"name": str(f.relative_to(raw)), "sha256": sha256(f), "bytes": f.stat().st_size} for f in files]


def ensure_master_keys() -> None:
    """Create the master api_keys.env template on first use."""
    if not API_KEYS_MASTER.exists():
        API_KEYS_MASTER.write_text(API_KEYS_TEMPLATE)


def copy_keys_into(proj: Path) -> None:
    """Sync the master api_keys.env into a project so the sealed-context model can read it."""
    ensure_master_keys()
    shutil.copy2(API_KEYS_MASTER, proj / "api_keys.env")


def key_names(path: Path) -> list[str]:
    """Names (not values) of keys set to a non-empty value in an api_keys.env file."""
    names = []
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if v.strip():
                    names.append(k.strip())
    return names


# --- sealing: global (gated/grounded) vs per-dataset (grounded2) -------------
def dataset_dirs(proj: Path) -> list[Path]:
    """Top-level dataset subdirs under data/raw/ (per-dataset seal layout)."""
    raw = proj / "data" / "raw"
    return sorted(d for d in raw.iterdir() if d.is_dir()) if raw.is_dir() else []


def normalize_flat_into_primary(proj: Path) -> None:
    """For per-dataset frameworks: move any files placed directly in data/raw/ into
    data/raw/primary/ so every dataset lives in its own sealable subdir."""
    raw = proj / "data" / "raw"
    if not raw.is_dir():
        return
    flat = [f for f in raw.iterdir() if f.is_file() and f.name != ".sealed"]
    if flat:
        primary = raw / "primary"
        primary.mkdir(exist_ok=True)
        for f in flat:
            shutil.move(str(f), str(primary / f.name))


def seal_dataset(proj: Path, dataset_dir: Path) -> dict:
    """Write data/raw/<dataset>/.sealed for one dataset; returns its record."""
    files = sorted(f for f in dataset_dir.rglob("*") if f.is_file() and f.name != ".sealed")
    recs = [{"name": str(f.relative_to(dataset_dir)), "sha256": sha256(f), "bytes": f.stat().st_size} for f in files]
    seal = {"sealed": now_iso(), "dataset": dataset_dir.name, "files": recs}
    (dataset_dir / ".sealed").write_text(json.dumps(seal, indent=2) + "\n")
    return {"dataset": dataset_dir.name, "files": recs}


def seal_all_unsealed(proj: Path) -> list[str]:
    """Seal every dataset subdir that has data but no .sealed yet. Returns sealed names."""
    sealed = []
    for d in dataset_dirs(proj):
        if (d / ".sealed").exists():
            continue
        if any(f.is_file() and f.name != ".sealed" for f in d.rglob("*")):
            seal_dataset(proj, d)
            sealed.append(d.name)
    return sealed


# --- gen --------------------------------------------------------------------
def cmd_gen(args: argparse.Namespace) -> None:
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
    #    framework.json is control-plane metadata and README.md is framework documentation —
    #    don't ship either into the runtime.
    for item in fw_dir.iterdir():
        if item.name in ("framework.json", "README.md"):
            continue
        dest = proj / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    for hook in (proj / ".claude" / "hooks").glob("*.sh"):
        hook.chmod(0o755)

    # 2) create the empty skeleton dirs the framework expects, plus data/raw/
    for rel in meta.get("skeleton_dirs", []):
        (proj / rel).mkdir(parents=True, exist_ok=True)
    raw = proj / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    if meta.get("seal_mode") == "per-dataset":
        # per-dataset sealing needs each dataset in its own subdir — give the user an
        # obvious place to paste files (left empty for a --no-data run).
        (raw / "primary").mkdir(exist_ok=True)

    # 3) sync the master API keys into the project (if the framework uses them)
    if meta.get("uses_api_keys"):
        copy_keys_into(proj)

    # 4) provenance stubs (data filled in at `run` time)
    domain = getattr(args, "domain", None)
    write_experiment_md(proj, name, fw, args.idea, inputs=[], launched=False, domain=domain)
    upsert_experiment(name, framework=fw, created=now_iso(), idea=(args.idea or "").strip(),
                      domain=(domain or "").strip(), status="generated")

    # frameworks that require ≥1 input: warn now if neither domain nor idea was given
    # (a dataset pasted into data/raw/ before `run` also satisfies the rule — enforced there).
    if meta.get("requires_input") and not ((domain or "").strip() or (args.idea or "").strip()):
        print(f"\n  ⚠ no --domain or --idea given. {fw!r} needs at least one input — "
              f"paste a dataset into data/raw/ before `run`, or re-gen with --domain/--idea.")

    rel = proj.relative_to(HERE)
    per_dataset = meta.get("seal_mode") == "per-dataset"
    no_data_ok = meta.get("supports_no_data")
    print(f"\nGenerated experiment {name!r} (framework: {fw})")
    if meta.get("uses_api_keys"):
        names = key_names(API_KEYS_MASTER)
        print(f"  api_keys.env synced ({'keys: ' + ', '.join(names) if names else 'no keys set yet — edit ' + str(API_KEYS_MASTER)})")
    print(f"\nNext:")
    if per_dataset:
        print(f"  1. paste this experiment's dataset into: {rel}/data/raw/primary/")
        print(f"     (one subdir per dataset — add more as {rel}/data/raw/<name>/; leave empty for --no-data)")
    else:
        print(f"  1. copy this experiment's dataset into:  {rel}/data/raw/")
    if no_data_ok:
        print(f"  2. python tool.py run {name}            (or `run {name} --no-data` to self-source)")
    else:
        print(f"  2. python tool.py run {name}")
    print(f"     run seals your data automatically — no manual seal step needed.")


# --- run --------------------------------------------------------------------
def cmd_run(args: argparse.Namespace) -> None:
    proj = PROJECTS_DIR / args.name
    if not proj.exists():
        die(f"no such project: {args.name!r}. Generate it first:  python tool.py gen {args.name}")
    prompt_file = proj / "prompt.md"
    if not prompt_file.exists():
        die(f"{args.name!r} is missing prompt.md — was it generated with `tool.py gen`?")

    e = next((x for x in load_registry().get("experiments", []) if x.get("name") == args.name), {})
    fw = e.get("framework", "?")
    meta = framework_meta(fw) if fw and fw != "?" else {}
    per_dataset = meta.get("seal_mode") == "per-dataset"
    domain = e.get("domain") or None

    # finish setup -----------------------------------------------------------
    no_data = getattr(args, "no_data", False)
    if no_data:
        if not meta.get("supports_no_data"):
            die(f"--no-data is not supported by framework {fw!r}. Use a self-sourcing framework "
                f"(e.g. 'grounded'/'grounded2'), which acquires and verifies its own data at the source gate.")
        data_mode = "self-sourced"
    else:
        # per-dataset frameworks: normalize loose files into data/raw/primary/ so each
        # dataset has its own sealable subdir.
        if per_dataset:
            normalize_flat_into_primary(proj)
        if not scan_raw(proj):
            die(f"data/raw/ is empty in {args.name!r}. Copy this experiment's dataset in first:\n"
                f"  cp <your_data> {proj.relative_to(HERE)}/data/raw/\n"
                f"or, for a self-sourcing framework, let the run acquire it:\n"
                f"  python tool.py run {args.name} --no-data")
        data_mode = "provided"

    for hook in (proj / ".claude" / "hooks").glob("*.sh"):  # ensure hooks are runnable
        hook.chmod(0o755)
    if meta.get("uses_api_keys"):  # re-sync latest keys from the master
        copy_keys_into(proj)

    # Seal provided data now so data/raw is immutable for the run. Self-sourced data
    # is sealed by the source gate (per dataset) after each data-checker passes.
    sealed_now = []
    if not no_data:
        if per_dataset:
            sealed_now = seal_all_unsealed(proj)
        elif scan_raw(proj):
            write_seal(proj, scan_raw(proj))
    inputs = scan_raw(proj)

    # ≥1-input rule (frameworks that declare requires_input, e.g. spirit): at least one of
    # {research area, idea, a dataset in data/raw/} must be present. data/raw is known now.
    if meta.get("requires_input") and not ((domain or "").strip() or (e.get("idea") or "").strip() or inputs):
        die(f"{args.name!r} ({fw}) has no input: provide at least one of a research area, an idea, "
            f"or a dataset.\n  - re-gen with --domain/--idea, or\n  - paste a dataset into "
            f"{proj.relative_to(HERE)}/data/raw/ and re-run.")

    write_experiment_md(proj, args.name, fw, e.get("idea") or None, inputs, launched=True,
                        data_mode=data_mode, domain=domain)
    upsert_experiment(args.name, run_started=now_iso(), status="launched", inputs=inputs, data_mode=data_mode)

    # emit the launch command + prompt --------------------------------------
    abs_proj = str(proj)
    if meta.get("uses_api_keys"):
        names = key_names(proj / "api_keys.env")
        print(f"\napi_keys.env: {'available — ' + ', '.join(names) if names else 'no keys set (edit ' + str(API_KEYS_MASTER) + ')'}")
    if no_data and not inputs:
        print(f"\nSetup complete for {args.name!r}: --no-data mode — data/raw/ is empty by design.")
        print("The source gate will acquire the dataset (data-finder), verify it (data-checker),")
        if per_dataset:
            print("and seal it PER DATASET (automatically). You can pair in more data later:  python tool.py augment", args.name, "--data <path>")
        print("(optional) mirror the self-sourced provenance into the registry:  python tool.py seal", args.name)
    else:
        total = sum(i["bytes"] for i in inputs)
        if no_data:
            sealed = ""
        elif per_dataset:
            sealed = f" — SEALED datasets: {', '.join(sealed_now)}" if sealed_now else " (already sealed)"
        else:
            sealed = " and SEALED (immutable)"
        print(f"\nSetup complete for {args.name!r}: {len(inputs)} input file(s), {total:,} bytes in data/raw/{sealed}")
        for i in inputs:
            print(f"  - {i['name']}  ({i['bytes']:,} bytes, sha256 {i['sha256'][:12]}…)")
        if per_dataset:
            print("Pair in more data mid-study with:  python tool.py augment", args.name, "--data <path> --name <slug>")

    print("\n" + "=" * 72)
    print("RUN IT — paste this command into your terminal:")
    print("=" * 72)
    print(f'\n  cd "{abs_proj}" && claude --dangerously-skip-permissions "$(cat prompt.md)"\n')
    print("(prompt.md is editable — tweak it to try a different process for this run.)")


# --- helpers shared by gen/run ---------------------------------------------
def write_experiment_md(proj: Path, name: str, fw: str, idea: str | None,
                        inputs: list[dict], launched: bool, data_mode: str = "provided",
                        domain: str | None = None) -> None:
    self_sourced = data_mode == "self-sourced"
    lines = [
        f"# Experiment: {name}",
        "",
        f"- **Framework:** {fw}",
        f"- **Generated:** {now_iso()}" if not launched else f"- **Launched:** {now_iso()}",
        f"- **Data mode:** {'SELF-SOURCED (--no-data) — acquire the dataset at the source gate' if self_sourced else 'PROVIDED — dataset supplied in data/raw/'}",
        "",
    ]
    if domain and domain.strip():
        lines += ["## Research area", "", domain.strip(), ""]
    # idea placeholder adapts: if a research area is given, the orchestrator may derive
    # the question from it (no idea required), otherwise prompt the user to fill one in.
    idea_placeholder = ("_(none — derive candidate questions from the research area above)_"
                        if (domain and domain.strip())
                        else "_(fill this in — the orchestrator reads this file)_")
    lines += [
        "## Research idea",
        "",
        (idea.strip() if idea else idea_placeholder),
        "",
        "## Inputs (data/raw/ — immutable once sealed)",
        "",
    ]
    if inputs:
        lines += [f"- `{i['name']}` — {i['bytes']:,} bytes — sha256 `{i['sha256'][:16]}…`" for i in inputs]
    elif self_sourced:
        lines.append("_(none yet — this is a --no-data run: the source gate (data-finder + data-checker) "
                     "acquires and verifies the dataset, then seals data/raw/.)_")
    else:
        lines.append("_(none yet — copy this experiment's dataset into data/raw/, then `tool.py run`)_")
    lines.append("")
    (proj / "EXPERIMENT.md").write_text("\n".join(lines))


def write_seal(proj: Path, inputs: list[dict]) -> None:
    """Freeze data/raw/ by recording each file's hash. Once data/.sealed exists,
    the protect_raw hook blocks every further write to data/raw/."""
    seal = {"sealed": now_iso(), "files": inputs}
    (proj / "data" / ".sealed").write_text(json.dumps(seal, indent=2) + "\n")


# --- helper commands --------------------------------------------------------
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
    on_disk = {p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()} if PROJECTS_DIR.is_dir() else set()
    names = sorted(set(reg) | on_disk)
    if not names:
        print("No experiments yet. Create one:  python tool.py gen <name>")
        return
    print(f"{'NAME':16s} {'FRAMEWORK':10s} {'CREATED':20s} STATUS")
    for name in names:
        proj = PROJECTS_DIR / name
        e = reg.get(name, {})
        fw = e.get("framework") or ("untracked" if proj.exists() else "?")
        status = "missing" if not proj.exists() else gate_status(proj)
        print(f"{name:16s} {fw:10s} {e.get('created', '-')[:19]:20s} {status}")


def gate_status(proj: Path) -> str:
    """Best-effort status: gate report if present, else infer from disk."""
    report = proj / "validation" / "report.json"
    if report.exists():
        try:
            gates = json.loads(report.read_text()).get("gates", [])
            # gates may be a list of {status:...} (test_01) or a dict gate->{status:...} (test_03)
            entries = list(gates.values()) if isinstance(gates, dict) else gates
            entries = [g for g in entries if isinstance(g, dict)]
            passed = sum(1 for g in entries if g.get("status") == "PASS")
            return f"{passed}/{len(entries)} gates PASS" if entries else "report present"
        except (json.JSONDecodeError, OSError, AttributeError):
            return "report unreadable"
    if (proj / "paper" / "main.tex").exists():
        return "drafting"
    raw = proj / "data" / "raw"
    if raw.is_dir() and any(raw.iterdir()):
        return "ready to run"
    return "generated (no data)"


def cmd_verify(args: argparse.Namespace) -> None:
    proj = PROJECTS_DIR / args.name
    runner = proj / "replication" / "run_all.sh"
    if not runner.exists():
        die(f"no replication/run_all.sh in {args.name!r} — has the pipeline run yet?")
    print(f"Running {runner.relative_to(HERE)} ...\n")
    raise SystemExit(subprocess.run(["bash", str(runner)], cwd=proj).returncode)


def openaireview_installed() -> bool:
    """True if the OpenAIReview Claude Code skill or its CLI is available."""
    if shutil.which("openaireview"):
        return True
    skills = Path.home() / ".claude" / "skills"
    return skills.is_dir() and any("openaireview" in p.name for p in skills.iterdir())


def cmd_review(args: argparse.Namespace) -> None:
    """POST-RUN: launch an independent OpenAIReview peer review of the finished paper
    via the Claude Code skill (uses your Claude subscription — no extra API credits) and
    feeds the LaTeX source directly (no OCR, more reliable than a PDF pass). Complements
    the framework's internal `referee` with an external review."""
    proj = PROJECTS_DIR / args.name
    if not proj.exists():
        die(f"no such project: {args.name!r}")
    rel_tex = args.tex or "paper/main.tex"
    tex = proj / rel_tex
    if not tex.exists():
        die(f"no LaTeX at {args.name}/{rel_tex} — has the run produced the paper yet? "
            f"(override the file with --tex <path relative to the project>)")

    if not openaireview_installed():
        print("OpenAIReview is not installed. Install it once (then reviews run free via your")
        print("Claude subscription — no extra API credits):\n")
        print("  pip install openaireview && openaireview install-skill\n")
        print(f"Then re-run:  python tool.py review {args.name}")
        print("(see `openaireview --help` if the install subcommand name differs in your version)")
        return

    # The skill takes a file path; a .tex is plain text, so it reviews the LaTeX directly
    # with NO OCR step (the only paid part of OpenAIReview, and only for PDFs).
    skill_prompt = f"/openaireview {rel_tex}"
    print(f"OpenAIReview — independent external review of {args.name}/{rel_tex}")
    print("  • runs via the Claude Code skill (your subscription; no extra API credits)")
    print("  • LaTeX input — no OCR")
    print(f"  • results (JSON) land in {proj.relative_to(HERE)}/review_results/")
    serve_cmd = f'cd "{proj}" && openaireview serve'
    if args.print_only:
        print("\nPaste this to launch the review:")
        print(f'\n  cd "{proj}" && claude --dangerously-skip-permissions "{skill_prompt}"\n')
        print("Then, to serve the results webpage, paste:")
        print(f'\n  {serve_cmd}\n')
        return
    print("\nLaunching ...\n")
    rc = subprocess.run(["claude", "--dangerously-skip-permissions", skill_prompt], cwd=proj).returncode
    print("\n" + "=" * 72)
    print("Review finished. To serve the results webpage, paste this:")
    print("=" * 72)
    print(f'\n  {serve_cmd}\n')
    raise SystemExit(rc)


def cmd_seal(args: argparse.Namespace) -> None:
    """Record provenance of whatever is in data/raw/ and freeze it. Use after a
    --no-data run has self-sourced its dataset (the source gate already sealed it
    during the run; this re-hashes from the control plane and records the inputs into
    the registry + EXPERIMENT.md). Per-dataset frameworks seal each dataset subdir."""
    proj = PROJECTS_DIR / args.name
    if not proj.exists():
        die(f"no such project: {args.name!r}")
    inputs = scan_raw(proj)
    if not inputs:
        die(f"data/raw/ is empty in {args.name!r}; nothing to seal.")
    e = next((x for x in load_registry().get("experiments", []) if x.get("name") == args.name), {})
    meta = framework_meta(e.get("framework")) if e.get("framework") in set(list_frameworks()) else {}
    if meta.get("seal_mode") == "per-dataset":
        normalize_flat_into_primary(proj)
        sealed_now = seal_all_unsealed(proj)
        inputs = scan_raw(proj)
        already = [d.name for d in dataset_dirs(proj) if d.name not in sealed_now]
        msg = f"sealed {sealed_now or '(none new)'}" + (f"; already sealed {already}" if already else "")
    else:
        write_seal(proj, inputs)
        msg = "sealed globally"
    write_experiment_md(proj, args.name, e.get("framework", "?"), e.get("idea") or None,
                        inputs, launched=True, data_mode=e.get("data_mode", "provided"),
                        domain=e.get("domain") or None)
    upsert_experiment(args.name, inputs=inputs, sealed=now_iso())
    total = sum(i["bytes"] for i in inputs)
    print(f"Sealed {args.name!r}: {len(inputs)} file(s), {total:,} bytes in data/raw/ — {msg} (now immutable).")
    for i in inputs:
        print(f"  - {i['name']}  ({i['bytes']:,} bytes, sha256 {i['sha256'][:12]}…)")


def cmd_augment(args: argparse.Namespace) -> None:
    """Pair in an ADDITIONAL dataset mid-study (e.g. weather, a policy-shock series).
    Copies files into data/raw/<slug>/ and seals just that subdir, leaving existing
    sealed datasets untouched. Only for per-dataset frameworks (e.g. grounded2)."""
    proj = PROJECTS_DIR / args.name
    if not proj.exists():
        die(f"no such project: {args.name!r}")
    e = next((x for x in load_registry().get("experiments", []) if x.get("name") == args.name), {})
    fw = e.get("framework")
    meta = framework_meta(fw) if fw in set(list_frameworks()) else {}
    if not meta.get("supports_augment") or meta.get("seal_mode") != "per-dataset":
        die(f"framework {fw!r} does not support data augmentation. Use a per-dataset framework (e.g. 'grounded2').")
    src = Path(args.data).expanduser().resolve()
    if not src.exists():
        die(f"--data path not found: {src}")
    slug = (args.name_ or (src.stem if src.is_file() else src.name)).strip().replace(" ", "_")
    dest = proj / "data" / "raw" / slug
    if (dest / ".sealed").exists():
        die(f"dataset {slug!r} already exists and is sealed in {args.name!r}. Choose another --name.")
    dest.mkdir(parents=True, exist_ok=True)
    files = [f for f in src.rglob("*") if f.is_file()] if src.is_dir() else [src]
    for f in files:
        shutil.copy2(f, dest / f.name)
    rec = seal_dataset(proj, dest)
    inputs = scan_raw(proj)
    upsert_experiment(args.name, inputs=inputs, augmented=now_iso())
    write_experiment_md(proj, args.name, fw, e.get("idea") or None, inputs, launched=True,
                        data_mode=e.get("data_mode", "provided"), domain=e.get("domain") or None)
    total = sum(i["bytes"] for i in rec["files"])
    print(f"Augmented {args.name!r} with dataset {slug!r}: {len(rec['files'])} file(s), {total:,} bytes — SEALED.")
    print(f"  -> data/raw/{slug}/  (existing sealed datasets untouched)")


def cmd_keys(_: argparse.Namespace) -> None:
    """Show the master API-keys file and which keys are set (values never printed)."""
    ensure_master_keys()
    names = key_names(API_KEYS_MASTER)
    print(f"Master API keys file: {API_KEYS_MASTER}")
    print(f"Keys set: {', '.join(names) if names else '(none — edit the file above to add e.g. CENSUS_API_KEY=...)'}")
    print("Edit that one file; `gen`/`run` sync it into each project's api_keys.env.")


def cmd_clean(args: argparse.Namespace) -> None:
    proj = PROJECTS_DIR / args.name
    if not proj.exists():
        die(f"no such project: {args.name!r}")
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
    if not args.yes and input("Proceed? [y/N] ").strip().lower() not in {"y", "yes"}:
        print("aborted.")
        return
    for t in existing:
        shutil.rmtree(t) if t.is_dir() else t.unlink()
    print("cleaned.")


# --- arg parsing ------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tool.py", description="MiddAR experiment control plane")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", aliases=["gen-project"], help="generate a project folder structure from a framework")
    g.add_argument("name")
    g.add_argument("--framework", default="gated", help="framework template (default: gated)")
    g.add_argument("--domain", default=None, help="research area/domain (written into EXPERIMENT.md; "
                   "domain-only runs let the framework generate candidate questions)")
    g.add_argument("--idea", default=None, help="research idea (written into EXPERIMENT.md)")
    g.add_argument("--force", action="store_true", help="overwrite config of an existing project (data preserved)")
    g.set_defaults(func=cmd_gen)

    r = sub.add_parser("run", aliases=["run-experiment"], help="finish setup and print the prompt to paste into Claude Code")
    r.add_argument("name")
    r.add_argument("--no-data", action="store_true",
                   help="self-sourcing run: don't require data/raw/ — the source gate finds/downloads/"
                        "generates and verifies the dataset (framework must support it, e.g. 'grounded')")
    r.set_defaults(func=cmd_run)

    sub.add_parser("list", help="list experiments and status").set_defaults(func=cmd_list)
    sub.add_parser("frameworks", help="list available frameworks").set_defaults(func=cmd_frameworks)

    v = sub.add_parser("verify", help="run an experiment's replication/run_all.sh")
    v.add_argument("name")
    v.set_defaults(func=cmd_verify)

    rv = sub.add_parser("review", help="POST-RUN: launch an independent OpenAIReview peer review of the paper via the Claude Code skill (your subscription, no extra API credits; reviews the LaTeX, no OCR)")
    rv.add_argument("name")
    rv.add_argument("--tex", default=None, metavar="PATH",
                    help="LaTeX file to review, relative to the project (default: paper/main.tex)")
    rv.add_argument("--print", dest="print_only", action="store_true",
                    help="just print the launch command instead of running it")
    rv.set_defaults(func=cmd_review)

    s = sub.add_parser("seal", help="OPTIONAL: mirror data/raw/ provenance into the registry (the agent/run already seal automatically)")
    s.add_argument("name")
    s.set_defaults(func=cmd_seal)

    a = sub.add_parser("augment", help="pair in an additional dataset mid-study (per-dataset frameworks, e.g. grounded2)")
    a.add_argument("name", help="experiment name")
    a.add_argument("--data", required=True, metavar="PATH", help="file or dir to add as a new dataset")
    a.add_argument("--name", dest="name_", default=None, metavar="SLUG",
                   help="dataset slug -> data/raw/<slug>/ (default: derived from the path)")
    a.set_defaults(func=cmd_augment)

    sub.add_parser("keys", help="show the master API-keys file and which keys are set").set_defaults(func=cmd_keys)

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
