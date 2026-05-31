#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

built=0
skipped=0

for json in kaomoji_*.json; do
  dict="${json%.json}.dict"

  if [ -f "$dict" ] && [ "$dict" -nt "$json" ]; then
    echo "$dict is up to date, skipping"
    skipped=$((skipped + 1))
    continue
  fi

  echo ""
  echo "=== Building $dict ==="
  python build_kaomoji_dict.py "$json"
  touch "$dict"
  built=$((built + 1))
done

echo ""
echo "Done: $built built, $skipped skipped"
