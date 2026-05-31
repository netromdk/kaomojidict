#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
HASHFILE="$VENV/.requirements-hash"
VERMIN_TARGET="3.10-"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

CURRENT_HASH=$(sha256sum "$SCRIPT_DIR/requirements-dev.txt" | awk '{print $1}')
if [ ! -f "$HASHFILE" ] || [ "$(cat "$HASHFILE")" != "$CURRENT_HASH" ]; then
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements-dev.txt"
  echo "$CURRENT_HASH" > "$HASHFILE"
fi

export PATH="$VENV/bin:$PATH"

mapfile -t ALL_PY < <(find "$SCRIPT_DIR" -name "*.py" \
                           -not -path "*/.venv/*" \
                           -not -path "*/aosp-dictionary-tools/*" \
                           -not -path "*/.git/*" | sort)
mapfile -t TOP_PY < <(find "$SCRIPT_DIR" -maxdepth 1 -name "*.py" | sort)
mapfile -t ALL_SH < <(find "$SCRIPT_DIR" -name "*.sh" \
                           -not -path "*/.venv/*" \
                           -not -path "*/aosp-dictionary-tools/*" \
                           -not -path "*/.git/*" | sort)

echo "--- flake8 ---"
flake8 --max-line-length=100 --indent-size=2 "${ALL_PY[@]}"

echo "--- bandit ---"
bandit --skip B101,B108 "${ALL_PY[@]}"

echo "--- vulture ---"
vulture --min-confidence=70 "${ALL_PY[@]}"

echo "--- pylint ---"
pylint -j 0 --max-line-length=100 \
  --disable=C0103,C0114,C0115,C0116,C0209,C0302,W0201,W0311,W0621,W0703 \
  --disable=R0801,R0902,R0903,R0904,R0911,R0912,R0913,R0914,R0915,R0916,R0917,R1702 \
  --disable=E1101,E1136 \
  "${ALL_PY[@]}"

echo "--- mypy ---"
mypy --strict "${TOP_PY[@]}"

echo "--- vermin ---"
vermin --target=${VERMIN_TARGET} --violations --no-tips "${ALL_PY[@]}"

echo "--- shellcheck ---"
shellcheck -x "${ALL_SH[@]}"

echo "--- pytest ---"
python3 -m pytest "$SCRIPT_DIR/tests/" --tb=short -v
