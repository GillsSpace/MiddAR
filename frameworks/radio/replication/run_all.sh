#!/usr/bin/env bash
# run_all.sh — SHIPPED radio primitive (extend, don't re-author).
# One-button, deterministic, crash-resilient reproduction (AEA-style).
#
# Flow:
#   1. verify the per-dataset seals (does NOT re-download self-sourced data)
#   2. run each analysis step listed in replication/manifest.json "steps" IN ORDER
#      (each step is a shell command run from the project root; split long ones so a
#      time-kill resumes rather than restarts — non-negotiable 20)
#   3. orphan-check the paper prose against validation/claims.json
#
# The orchestrator fills manifest.json "steps" as the econometrician produces scripts.
# Re-running is idempotent: steps should overwrite their outputs deterministically.
set -euo pipefail
cd "$(dirname "$0")/.."   # project root

SEED="${MIDDAR_SEED:-20240626}"
export PYTHONHASHSEED="$SEED"
export MIDDAR_SEED="$SEED"
echo "== radio reproduction (seed=$SEED) =="

echo "-- [1/3] verifying data seals"
python3 replication/verify_seals.py

echo "-- [2/3] running analysis steps from manifest.json"
mapfile -t STEPS < <(python3 -c '
import json, sys
from pathlib import Path
m = Path("replication/manifest.json")
if not m.exists():
    sys.exit(0)
for s in json.loads(m.read_text()).get("steps", []):
    print(s if isinstance(s, str) else s.get("cmd", ""))
')
if [[ "${#STEPS[@]}" -eq 0 ]]; then
  echo "   (no steps registered yet — populate replication/manifest.json \"steps\")"
else
  i=0
  for step in "${STEPS[@]}"; do
    [[ -z "$step" ]] && continue
    i=$((i+1))
    echo "   [step $i] $step"
    bash -c "$step"
  done
fi

echo "-- [3/3] orphan-checking paper prose"
python3 replication/orphan_check.py

echo "== reproduction complete =="
