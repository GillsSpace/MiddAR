#!/usr/bin/env bash
input=$(cat)
path=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
if [[ "$path" == *"data/raw/"* ]]; then
  echo "BLOCKED: data/raw is immutable. Write outputs to work/ or paper/ instead." >&2
  exit 2
fi
exit 0
