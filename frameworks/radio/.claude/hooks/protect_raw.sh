#!/usr/bin/env bash
# Per-dataset raw-data immutability. Each dataset lives in data/raw/<dataset>/ and is
# writable ONLY until its own data/raw/<dataset>/.sealed exists. Once a dataset is
# sealed it is frozen; OTHER (unsealed) datasets stay writable, which is what lets the
# run add a complementary dataset later. A legacy global data/.sealed, if present,
# freezes everything under data/raw. Seal files themselves can never be edited.
# Runs with cwd = project root.
input=$(cat)
decision=$(MIDDAR_HOOK_INPUT="$input" python3 -c '
import os, json
try:
    path = json.loads(os.environ.get("MIDDAR_HOOK_INPUT", "{}")).get("tool_input", {}).get("file_path", "") or ""
except Exception:
    print("ALLOW"); raise SystemExit

# 1) Never allow editing/deleting a seal file that already exists.
if path.endswith(".sealed"):
    rel = path
    if "data/raw/" in path:
        rel = "data/raw/" + path.split("data/raw/", 1)[1]
    elif "data/.sealed" in path:
        rel = "data/.sealed"
    if os.path.exists(rel):
        print("BLOCK:a .sealed file is an immutability seal and must not be edited or deleted."); raise SystemExit

# 2) Only writes under data/raw/ are otherwise restricted.
if "data/raw/" not in path:
    print("ALLOW"); raise SystemExit

# 3) A legacy/global seal freezes all of data/raw.
if os.path.exists("data/.sealed"):
    print("BLOCK:data/raw is sealed globally (data/.sealed). Write outputs to work/ or paper/ instead."); raise SystemExit

# 4) Per-dataset seal: block only if THIS dataset subdir is sealed.
rest = path.split("data/raw/", 1)[1]
parts = [p for p in rest.split("/") if p]
dataset = parts[0] if len(parts) >= 2 else None  # need <dataset>/<file>
if dataset and os.path.exists(os.path.join("data/raw", dataset, ".sealed")):
    print("BLOCK:dataset data/raw/%s is sealed (verified & frozen at the source gate). Write outputs to work/ or paper/ instead." % dataset); raise SystemExit

print("ALLOW")
')
if [[ "$decision" == BLOCK:* ]]; then
  echo "BLOCKED: ${decision#BLOCK:}" >&2
  exit 2
fi
exit 0
