#!/usr/bin/env bash
# Raw-data immutability via a seal. data/raw is writable ONLY until data/.sealed
# exists (so the source gate can deposit a self-sourced dataset). Once sealed,
# every write to data/raw is blocked — same guarantee as a provided-data run.
input=$(cat)
path=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Never allow tampering with the seal itself.
if [[ "$path" == *"data/.sealed"* && -f "data/.sealed" ]]; then
  echo "BLOCKED: data/.sealed is the immutability seal and must not be edited or deleted." >&2
  exit 2
fi

if [[ "$path" == *"data/raw/"* ]]; then
  if [[ -f "data/.sealed" ]]; then
    echo "BLOCKED: data/raw is sealed (immutable). It was verified and frozen at the source gate; write outputs to work/ or paper/ instead." >&2
    exit 2
  fi
  # not yet sealed: the source gate is allowed to deposit the dataset here.
fi
exit 0
