#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

json="kaomoji.json"
built=0
skipped=0

if [ ! -f "$json" ]; then
  echo "error: $json not found" >&2
  exit 1
fi

locales=$(jq -r '.locales[]' "$json")

for locale in $locales; do
  combined="emoji_${locale}.combined"

  if [ ! -f "$combined" ]; then
    echo "error: $combined not found. Download it first (see README)" >&2
    skipped=$((skipped + 1))
    continue
  fi

  # Locale-specific tags only.
  dict="kaomoji_${locale}.dict"
  old=$([[ -f "$dict" ]] && stat -c %Y "$dict" || echo 0)
  src_old=$(stat -c %Y "$json")
  comb_old=$(stat -c %Y "$combined")

  if [ "$old" -ge "$src_old" ] && [ "$old" -ge "$comb_old" ]; then
    echo "$dict is up to date, skipping"
    skipped=$((skipped + 1))
  else
    echo ""
    echo "=== Building $dict (merged with $combined) ==="
    python build_kaomoji_dict.py "$json" --no-bump --locale "$locale" \
      --merge-combined "$combined" --output "$dict"
    touch "$dict"
    built=$((built + 1))
  fi

  # All locales' tags merged.
  dict_all="kaomoji_${locale}_combined.dict"
  old_all=$([[ -f "$dict_all" ]] && stat -c %Y "$dict_all" || echo 0)

  if [ "$old_all" -ge "$src_old" ] && [ "$old_all" -ge "$comb_old" ]; then
    echo "$dict_all is up to date, skipping"
    skipped=$((skipped + 1))
  else
    echo ""
    echo "=== Building $dict_all (merged + all locales) ==="
    python build_kaomoji_dict.py "$json"  --no-bump --locale "$locale" --all-locales \
      --merge-combined "$combined" --output "$dict_all"
    touch "$dict_all"
    built=$((built + 1))
  fi
done

echo ""
echo "Done: $built built, $skipped skipped"
