#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

built=0
skipped=0

for json in kaomoji_*.json; do
  locale=$(jq -r '.locale // "en"' "$json")
  combined="emoji_${locale}.combined"
  dict="${json%.json}.dict"

  if [ ! -f "$combined" ]; then
    echo "error: $combined not found. Download it first (see README)"
    skipped=$((skipped + 1))
    continue
  fi

  if [ -f "$dict" ] && [ "$dict" -nt "$json" ] && [ "$dict" -nt "$combined" ]; then
    echo "$dict is up to date, skipping"
    skipped=$((skipped + 1))
    continue
  fi

  echo ""
  echo "=== Building $dict (merged with $combined) ==="
  python build_kaomoji_dict.py "$json" --merge-combined "$combined" --output "$dict"
  touch "$dict"
  built=$((built + 1))
done

echo ""
echo "Done: $built built, $skipped skipped"
