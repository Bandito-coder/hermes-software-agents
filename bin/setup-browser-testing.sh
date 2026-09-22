#!/usr/bin/env bash
# setup-browser-testing.sh — one-time environment provisioner for browser smoke testing.
#
# Installs:
#   - geckodriver >= 0.35.0  -> $SMOKE_BIN_DIR (default: ~/.local/bin; /usr/local/bin if writable)
#   - Python venv            -> $SMOKE_VENV (default: ~/.hermes/browser-smoke-venv)
#     containing selenium (optional extra; the skill's stdlib client needs no third-party
#     packages — selenium is used only when the "selenium" check set is selected).
#
# Idempotent: safe to re-run; skips pieces already present. Never configures PATH
# (callers that need it should reference $HOME/.local/bin explicitly).
#
# Usage:
#   bash setup-browser-testing.sh
#   SMOKE_BIN_DIR=/custom/bin SMOKE_VENV=/opt/smoke-venv bash setup-browser-testing.sh
#
# Requires: bash, curl (or wget), tar, python3 >= 3.8, ~/.local/bin on PATH.
set -euo pipefail

GECKODRIVER_VERSION="${GECKODRIVER_VERSION:-v0.35.0}"
GECKODRIVER_RELEASE="${GECKODRIVER_RELEASE:-https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz}"

SMOKE_BIN_DIR="${SMOKE_BIN_DIR:-}"
if [[ -z "$SMOKE_BIN_DIR" ]]; then
  if [[ -w /usr/local/bin ]]; then
    SMOKE_BIN_DIR=/usr/local/bin
  else
    SMOKE_BIN_DIR="${HOME}/.local/bin"
    mkdir -p "$SMOKE_BIN_DIR"
  fi
fi
SMOKE_VENV="${SMOKE_VENV:-${HOME}/.hermes/browser-smoke-venv}"
TMPDIR_SAFE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_SAFE"' EXIT

pass()  { printf '::setup:: %-28s ::result:: PASS\n' "$1"; }
fail()  { printf '::setup:: %-28s ::result:: FAIL ::output:: %s\n' "$1" "$2"; exit 1; }

# --- 1. Firefox -----------------------------------------------------------
if command -v firefox >/dev/null 2>&1; then
  pass "firefox"
else
  fail "firefox" "firefox binary not found on PATH. Install Firefox (ESR recommended) first."
fi

# --- 2. geckodriver -------------------------------------------------------
if command -v geckodriver >/dev/null 2>&1; then
  ver="$(geckodriver --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  if [[ -n "$ver" ]] && python3 -c "import sys; sys.exit(0 if tuple(map(int,'$ver'.split('.'))) >= (0,35,0) else 1)"; then
    pass "geckodriver ($ver)"
  else
    fail "geckodriver" "found geckodriver $ver but need >= 0.35.0; remove it and re-run"
  fi
else
  echo "::setup:: downloading geckodriver ${GECKODRIVER_VERSION}"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 120 "$GECKODRIVER_RELEASE" -o "$TMPDIR_SAFE/geckodriver.tar.gz" \
      || fail "geckodriver" "download failed: $GECKODRIVER_RELEASE"
  elif command -v wget >/dev/null 2>&1; then
    wget -q --timeout=120 -O "$TMPDIR_SAFE/geckodriver.tar.gz" "$GECKODRIVER_RELEASE" \
      || fail "geckodriver" "download failed: $GECKODRIVER_RELEASE"
  else
    fail "geckodriver" "need curl or wget to download geckodriver"
  fi
  tar -xzf "$TMPDIR_SAFE/geckodriver.tar.gz" -C "$TMPDIR_SAFE"
  install -m 0755 "$TMPDIR_SAFE/geckodriver" "$SMOKE_BIN_DIR/geckodriver"
  pass "geckodriver (installed -> $SMOKE_BIN_DIR/geckodriver)"
fi

# --- 3. Python venv -------------------------------------------------------
if [[ -x "$SMOKE_VENV/bin/python" ]]; then
  pass "venv (reusing $SMOKE_VENV)"
else
  echo "::setup:: creating venv at $SMOKE_VENV"
  python3 -m venv "$SMOKE_VENV" || fail "venv" "could not create venv at $SMOKE_VENV"
  pass "venv"
fi

# --- 4. selenium (optional; best-effort) ----------------------------------
# The skill's default check sets run with the stdlib client only. selenium is
# installed so the extra "selenium-basics" check set can be used when present.
if ! "$SMOKE_VENV/bin/python" -c 'import selenium' >/dev/null 2>&1; then
  echo "::setup:: installing selenium into $SMOKE_VENV (optional)"
  if ! "$SMOKE_VENV/bin/python" -m pip install --quiet --disable-pip-version-check selenium==4.27.1 >/dev/null 2>&1; then
    echo "::setup:: selenium           ::result:: WARN (optional extra not installed; stdlib client unaffected)"
  else
    pass "selenium (venv)"
  fi
else
  pass "selenium (venv)"
fi

# --- 5. verify driver boots -----------------------------------------------
"$SMOKE_BIN_DIR/geckodriver" --version >/dev/null 2>&1 \
  || fail "geckodriver-boot" "geckodriver does not run"
pass "geckodriver-boot"

echo
echo "Environment ready."
echo "  geckodriver : $SMOKE_BIN_DIR/geckodriver"
echo "  venv python : $SMOKE_VENV/bin/python"
echo "Next: source the venv (or pass SMOKE_VENV to smoke_run.sh), then run a smoke test."