#!/usr/bin/env bash
set -uo pipefail

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
  "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements-dev.txt" || \
    echo "warning: pip install failed, linters may be missing" >&2
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

failures=0
failed_linters=""

echo "--- flake8 ---"
flake8 --max-line-length=100 --indent-size=2 "${ALL_PY[@]}" || \
  { echo "FAILED: flake8"; failures=$((failures + 1)); failed_linters="$failed_linters flake8,"; }

echo "--- bandit ---"
bandit --skip B101,B108 "${ALL_PY[@]}" || \
  { echo "FAILED: bandit"; failures=$((failures + 1)); failed_linters="$failed_linters bandit,"; }

echo "--- vulture ---"
vulture --min-confidence=70 "${ALL_PY[@]}" || \
  { echo "FAILED: vulture"; failures=$((failures + 1)); failed_linters="$failed_linters vulture,"; }

echo "--- pylint ---"
pylint -j 0 --max-line-length=100 \
  --disable=C0103,C0114,C0115,C0116,C0209,C0302,W0201,W0311,W0621,W0703 \
  --disable=R0801,R0902,R0903,R0904,R0911,R0912,R0913,R0914,R0915,R0916,R0917,R1702 \
  --disable=E1101,E1136 \
  "${ALL_PY[@]}" || \
  { echo "FAILED: pylint"; failures=$((failures + 1)); failed_linters="$failed_linters pylint,"; }

echo "--- mypy ---"
mypy --strict "${TOP_PY[@]}" || \
  { echo "FAILED: mypy"; failures=$((failures + 1)); failed_linters="$failed_linters mypy,"; }

echo "--- vermin ---"
vermin --target=${VERMIN_TARGET} --violations --no-tips "${ALL_PY[@]}" || \
  { echo "FAILED: vermin"; failures=$((failures + 1)); failed_linters="$failed_linters vermin,"; }

echo "--- shellcheck ---"
shellcheck -x "${ALL_SH[@]}" || \
  { echo "FAILED: shellcheck"; failures=$((failures + 1)); failed_linters="$failed_linters shellcheck,"; }

echo "--- pytest ---"
python3 -m pytest "$SCRIPT_DIR/tests/" --tb=short -v || \
  { echo "FAILED: pytest"; failures=$((failures + 1)); failed_linters="$failed_linters pytest,"; }

echo ""
if [ "$failures" -eq 0 ]; then
  echo "All checks passed."
else
  echo "FAILURES: $failures checker(s) reported errors:${failed_linters%,}"
fi
exit "$failures"
