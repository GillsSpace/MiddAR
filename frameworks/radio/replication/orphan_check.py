#!/usr/bin/env python3
"""orphan_check.py — SHIPPED radio primitive (extend, don't re-author).

Enforces non-negotiable 3 (no orphan numbers): every meaningful numeral in the paper
prose (paper/main.tex + paper/sections/*.tex) must map to a registered claim in
validation/claims.json. Flags numerals that have no matching registered value.

claims.json may be a list of entries or {"claims": [...]}. Each entry should carry a
numeric `value` (and ideally `units`, `script`, `log` for provenance). This checker reads
`value`; the units/SE checks live in the experiment-auditor.

Exempt by default: 4-digit years (1900–2099); numbers attached to \\ref/\\eqref/\\cite/
\\label/\\section/\\cite*/\\pageref; pure structural tokens. Add extra exemptions (one
literal token per line, e.g. `5` or `95` or `0.05`) in replication/orphan_allowlist.txt.

Exit 0 => every prose numeral is registered or exempt. Exit 1 => orphan numerals found.

Usage:
    python3 replication/orphan_check.py
    python3 replication/orphan_check.py --tol 0.005      # abs tolerance for matching
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
CLAIMS = ROOT / "validation" / "claims.json"
ALLOWLIST = ROOT / "replication" / "orphan_allowlist.txt"

NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")  # int or proper decimal; no trailing bare dot
# strip these LaTeX constructs (and their numeric args) before scanning
STRIP_CMDS = re.compile(
    r"\\(?:ref|eqref|pageref|label|cite[a-z]*|input|include|autoref|cref|Cref)\s*\{[^}]*\}"
)
COMMENT = re.compile(r"(?<!\\)%.*")


def load_claim_values():
    if not CLAIMS.exists():
        return None
    try:
        data = json.loads(CLAIMS.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"orphan_check: cannot parse {CLAIMS} ({e})")
        return None
    entries = data.get("claims", data) if isinstance(data, dict) else data
    vals = []
    for e in entries if isinstance(entries, list) else []:
        v = e.get("value") if isinstance(e, dict) else e
        try:
            vals.append(abs(float(v)))
        except (TypeError, ValueError):
            continue
    return vals


def load_allowlist():
    toks = set()
    if ALLOWLIST.exists():
        for line in ALLOWLIST.read_text().splitlines():
            t = line.strip()
            if t and not t.startswith("#"):
                toks.add(t)
    return toks


def normalize(tok: str):
    t = tok.replace(",", "").rstrip(".")
    try:
        return abs(float(t))
    except ValueError:
        return None


def main() -> int:
    tol = 0.005
    if "--tol" in sys.argv:
        tol = float(sys.argv[sys.argv.index("--tol") + 1])

    claim_vals = load_claim_values()
    if claim_vals is None:
        print("orphan_check: validation/claims.json missing or empty — register claims "
              "at estimate time (non-negotiable 15) before the draft. FAIL.")
        return 1
    allow = load_allowlist()

    tex_files = []
    if (PAPER / "main.tex").exists():
        tex_files.append(PAPER / "main.tex")
    tex_files += sorted((PAPER / "sections").glob("*.tex")) if (PAPER / "sections").exists() else []
    if not tex_files:
        print("orphan_check: no paper/*.tex yet — nothing to check (ok pre-draft).")
        return 0

    orphans = []
    for fp in tex_files:
        for lineno, raw in enumerate(fp.read_text().splitlines(), 1):
            line = STRIP_CMDS.sub(" ", COMMENT.sub("", raw))
            for m in NUM.finditer(line):
                tok = m.group(0)
                if tok in allow:
                    continue
                val = normalize(tok)
                if val is None:
                    continue
                # exempt 4-digit years
                if val.is_integer() and 1900 <= val <= 2099 and "." not in tok:
                    continue
                # match against any registered claim within tolerance (abs or 0.5% rel)
                if any(abs(val - c) <= max(tol, 0.005 * max(val, c)) for c in claim_vals):
                    continue
                orphans.append((fp.relative_to(ROOT), lineno, tok, raw.strip()[:90]))

    if orphans:
        print(f"orphan_check: FAIL — {len(orphans)} unregistered numeral(s):")
        for fp, ln, tok, ctx in orphans[:60]:
            print(f"  {fp}:{ln}  «{tok}»   {ctx}")
        if len(orphans) > 60:
            print(f"  … and {len(orphans) - 60} more.")
        print("Register each in validation/claims.json, or add a literal exemption to "
              "replication/orphan_allowlist.txt.")
        return 1
    print(f"orphan_check: OK — every prose numeral maps to a registered claim "
          f"({len(claim_vals)} claims, {len(tex_files)} tex file(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
