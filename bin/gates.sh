#!/usr/bin/env bash
# gates.sh — stack-detecting gate runner
# Exit codes: 0 = all pass, 1 = gate failed, 2 = no stack detected
# Output: ::gate:: <name>  /  ::result:: PASS|FAIL  /  ::output:: (on failure)

set -u
# Run in the directory the caller invoked us from (the project root)
# If gates.sh is in bin/ and invoked as ../bin/gates.sh, pwd is the project root

GATE_FAILED=0

run_gate() {
    local name="$1"; shift
    echo "::gate:: $name"
    if output=$("$@" 2>&1); then
        echo "::result:: PASS"
    else
        echo "::result:: FAIL"
        echo "::output::"
        echo "$output" | head -50
        GATE_FAILED=1
    fi
}

run_gate_silent_pass() {
    local name="$1"; shift
    echo "::gate:: $name"
    if output=$("$@" 2>&1); then
        echo "::result:: PASS"
    else
        echo "::result:: FAIL"
        echo "::output::"
        echo "$output" | head -50
        GATE_FAILED=1
    fi
}

# ---- Stack detection ----

if [[ -f "manage.py" ]]; then
    STACK="django"
elif [[ -f "requirements.txt" || -f "pyproject.toml" || -f "setup.py" ]]; then
    STACK="python"
elif [[ -f "package.json" ]]; then
    STACK="node"
else
    echo "::gate:: stack-detection"
    echo "::result:: FAIL"
    echo "::output::"
    echo "No stack detected. Expected one of: manage.py, requirements.txt, pyproject.toml, setup.py, package.json"
    exit 2
fi

echo "Detected stack: $STACK"

# ---- Python / Django gates ----

if [[ "$STACK" == "python" || "$STACK" == "django" ]]; then
    PY="python3"

    # deps: can we import the project's main module(s)? (lightweight check)
    if [[ -f "requirements.txt" ]]; then
        echo "::gate:: deps"
        missing=$($PY -c "
import importlib, re, sys
missing = []
for line in open('requirements.txt'):
    line = line.strip()
    if not line or line.startswith('#'): continue
    pkg = re.split(r'[><=!~\[]', line)[0].strip()
    pkg = pkg.replace('-', '_')
    if pkg in ('pytest','pip','setuptools','wheel'): continue
    try: importlib.import_module(pkg)
    except ImportError: missing.append(pkg)
if missing:
    print('Missing packages: ' + ', '.join(missing)); sys.exit(1)
print('ok')
" 2>&1)
        if [[ $? -eq 0 ]]; then echo "::result:: PASS"; else
            echo "::result:: FAIL"; echo "::output::"; echo "$missing"; GATE_FAILED=1
        fi
    fi

    # lint: pyflakes if available, else ruff, else skip with advisory
    if command -v ruff >/dev/null 2>&1; then
        run_gate "lint" ruff check .
    elif $PY -c "import pyflakes" 2>/dev/null; then
        run_gate "lint" $PY -m pyflakes .
    else
        echo "::gate:: lint"
        echo "::result:: PASS"
        echo "  (no linter installed — skipped)"
    fi

    # typecheck: mypy if available
    if command -v mypy >/dev/null 2>&1 || $PY -c "import mypy" 2>/dev/null; then
        run_gate "typecheck" $PY -m mypy . --ignore-missing-imports --no-error-summary 2>/dev/null || true
        # mypy returns nonzero on findings; the run_gate above already handled output
    else
        echo "::gate:: typecheck"
        echo "::result:: PASS"
        echo "  (no typechecker installed — skipped)"
    fi

    # django-check + migrations (django only)
    if [[ "$STACK" == "django" ]]; then
        run_gate "django-check" $PY manage.py check
        run_gate "migrations" $PY manage.py makemigrations --check --dry-run
    fi

    # test: pytest
    if command -v pytest >/dev/null 2>&1 || $PY -m pytest --version >/dev/null 2>&1; then
        run_gate "test" $PY -m pytest -q
    else
        echo "::gate:: test"
        echo "::result:: FAIL"
        echo "::output::"
        echo "pytest not installed"
        GATE_FAILED=1
    fi
fi

# ---- Node gates ----

if [[ "$STACK" == "node" ]]; then
    [[ -f package-lock.json ]] && run_gate "deps" npm ci --silent
    pkg_scripts=$(node -e "const p=require('./package.json').scripts||{}; console.log(Object.keys(p).join(' '))")
    [[ "$pkg_scripts" == *"lint"* ]] && run_gate "lint" npm run lint --silent
    [[ "$pkg_scripts" == *"typecheck"* ]] && run_gate "typecheck" npm run typecheck --silent
    [[ "$pkg_scripts" == *"test"* ]] && run_gate "test" npm test --silent
    [[ "$pkg_scripts" == *"build"* ]] && run_gate "build" npm run build --silent
fi

exit $GATE_FAILED
