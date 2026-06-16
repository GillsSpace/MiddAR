#!/usr/bin/env bash
# One-command reproduction: regenerates manifest, all claims, tables, figures, and the PDF
# from data/raw/ only. Halts on any error.
set -euo pipefail

# repo root = parent of this script's directory
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
export PYTHONHASHSEED=0   # deterministic dict/string hashing across runs

echo "== [0/11] reset generated artifacts (data/raw is never touched) =="
rm -f paper/tables/table1_main.tex paper/tables/table2_robustness.tex paper/tables/table3_inference.tex
rm -f paper/figures/fig1_attenuation.png paper/figures/fig2_raw_gradient.png
printf '{\n  "claims": []\n}\n' > validation/claims.json

echo "== [1/11] AUDIT      ==" ; $PY work/01_audit/audit.py
echo "== [2/11] PROFILE    ==" ; $PY work/02_profile/profile.py
echo "== [3/11] ESTIMATE   ==" ; $PY work/04_analysis/estimate.py
echo "== [4/11] DIAGNOSTICS ==" ; $PY work/04_analysis/diagnostics.py
echo "== [5/11] ROBUSTNESS ==" ; $PY work/05_robustness/robustness.py
echo "== [6/11] REFEREE FIX r1 ==" ; $PY work/05_robustness/referee_fixes.py
echo "== [7/11] REFEREE FIX r2 ==" ; $PY work/05_robustness/referee_fixes2.py
echo "== [8/11] EXTRA INFERENCE ==" ; $PY work/05_robustness/extra_inference.py
echo "== [9/11] REFEREE FIX r3 ==" ; $PY work/05_robustness/referee_fixes3.py
echo "== [10/11] BUILD TABLES ==" ; $PY work/05_robustness/make_tables.py
echo "== [11/11] ORPHAN-NUMBER CHECK ==" ; $PY validation/orphan_check.py

echo "== COMPILE PDF (optional; skipped if no pdflatex) =="
if command -v pdflatex >/dev/null 2>&1; then
  ( cd paper && pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/tex1.log 2>&1 \
      && pdflatex -interaction=nonstopmode -halt-on-error main.tex >/tmp/tex2.log 2>&1 ) \
      && echo "PDF: paper/main.pdf" || { echo "pdflatex failed; see /tmp/tex2.log"; tail -20 /tmp/tex2.log; }
else
  echo "pdflatex not found; skipping PDF."
fi
echo "== run_all.sh DONE =="
