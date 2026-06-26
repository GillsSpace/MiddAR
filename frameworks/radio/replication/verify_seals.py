#!/usr/bin/env python3
"""verify_seals.py — SHIPPED radio primitive (extend, don't re-author).

Re-verifies every sealed dataset under data/raw/<dataset>/ against its own
data/raw/<dataset>/.sealed manifest (and a legacy global data/.sealed, if present).
Recomputes each file's sha256 and compares to the recorded hash. Does NOT re-download.

Exit 0 => every sealed file matches. Exit 1 => a mismatch / missing file / unreadable seal.

Usage:
    python3 replication/verify_seals.py            # verify all sealed datasets
    python3 replication/verify_seals.py --quiet    # only print on failure
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_seal(seal_path: Path, base: Path, problems: list) -> int:
    """Verify one .sealed manifest; base is the dir its file names are relative to."""
    try:
        seal = json.loads(seal_path.read_text())
    except Exception as e:  # noqa: BLE001
        problems.append(f"{seal_path}: unreadable seal ({e})")
        return 0
    n = 0
    for entry in seal.get("files", []):
        name, want = entry.get("name"), entry.get("sha256")
        if not name or not want:
            continue
        fp = base / name
        if not fp.exists():
            problems.append(f"{seal_path.parent.name}/{name}: sealed file is missing")
            continue
        got = sha256(fp)
        if got != want:
            problems.append(f"{seal_path.parent.name}/{name}: sha256 mismatch "
                            f"(sealed {want[:12]}…, found {got[:12]}…)")
        else:
            n += 1
    return n


def main() -> int:
    quiet = "--quiet" in sys.argv
    problems: list = []
    verified = 0
    sealed_any = False

    if not RAW.exists():
        print("verify_seals: no data/raw/ — nothing to verify (ok for a code-only stage).")
        return 0

    # legacy global seal
    global_seal = ROOT / "data" / ".sealed"
    if global_seal.exists():
        sealed_any = True
        verified += check_seal(global_seal, RAW, problems)

    # per-dataset seals
    for seal_path in sorted(RAW.glob("*/.sealed")):
        sealed_any = True
        verified += check_seal(seal_path, seal_path.parent, problems)

    if not sealed_any:
        print("verify_seals: no .sealed manifests found under data/raw/ — nothing sealed yet.")
        return 0

    if problems:
        print(f"verify_seals: FAIL — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    if not quiet:
        print(f"verify_seals: OK — {verified} sealed file(s) match their hashes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
