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

locales=$(python3 -c "
import json, sys
data = json.load(open('$json'))
for loc in data['locales']:
    print(loc)
")

for locale in $locales; do
  # Locale-specific tags only.
  dict="kaomoji_${locale}.dict"
  old=$(python3 -c "
import os.path
p = '$dict'; print(int(os.path.getmtime(p)) if os.path.exists(p) else 0)
")
  src_old=$(python3 -c "
import os.path; print(int(os.path.getmtime('$json')))
")

  if [ "$old" -ge "$src_old" ]; then
    echo "$dict is up to date, skipping"
    skipped=$((skipped + 1))
  else
    echo ""
    echo "=== Building $dict ==="
    python build_kaomoji_dict.py "$json" --locale "$locale" --output "$dict"
    touch "$dict"
    built=$((built + 1))
  fi

  # All locales' tags merged.
  dict_all="kaomoji_${locale}_all_locales.dict"
  old_all=$(python3 -c "
import os.path
p = '$dict_all'; print(int(os.path.getmtime(p)) if os.path.exists(p) else 0)
")

  if [ "$old_all" -ge "$src_old" ]; then
    echo "$dict_all is up to date, skipping"
    skipped=$((skipped + 1))
  else
    echo ""
    echo "=== Building $dict_all ==="
    python build_kaomoji_dict.py "$json" --locale "$locale" --all-locales --output "$dict_all"
    touch "$dict_all"
    built=$((built + 1))
  fi
done

echo ""
echo "Done: $built built, $skipped skipped"
