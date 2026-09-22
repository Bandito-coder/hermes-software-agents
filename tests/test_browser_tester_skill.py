"""Structural + behavioral tests for the browser-tester skill and tooling.

A-series (structural, no live browser): frontmatter validity, verdict contract
present in SKILL.md, scripts exist and are syntactically valid, permission tier
is execute-only (no write instructions).

B-series (behavioral, live geckodriver+Firefox): a real smoke run against the
fixture app produces a valid PASS report and a valid FAIL report with a
failure screenshot, and cleans up its geckodriver/firefox processes.

Run (B-series ERRORS loudly, never silently skips, when no geckodriver is
available — pass/exit 0 requires the driver resolvable):
    export GECKODRIVER_BIN=/path/to/geckodriver   # sandbox: /tmp/gecko-dl/geckodriver
    python3 -m pytest tests/test_browser_tester_skill.py -q
or directly:
    python3 tests/test_browser_tester_skill.py
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(REPO, "agents")
BIN_DIR = os.path.join(REPO, "bin")
FIXTURE = os.path.join(REPO, "tests", "fixture", "smoke_fixture.py")

# Resolve the geckodriver binary: $GECKODRIVER_BIN wins, then PATH, then the
# canonical /usr/local/bin location (what bin/setup-browser-testing.sh installs).
GECKODRIVER_BIN = (
    os.environ.get("GECKODRIVER_BIN")
    or shutil.which("geckodriver")
    or "/usr/local/bin/geckodriver"
)
DRIVER_READY = os.path.isfile(GECKODRIVER_BIN)

# Used by the B-series tests: failure (ERROR), never a silent skip, so the
# suite cannot report green while the live-browser checks went unexercised.
_NO_DRIVER_MSG = (
    f"geckodriver not found at '{GECKODRIVER_BIN}' — B-series behavioral tests "
    "cannot run. Set GECKODRIVER_BIN, add geckodriver to PATH, or run "
    "bin/setup-browser-testing.sh (see banner above)."
)


def _require_driver():
    """B-series gate: ERROR loudly (never silently skip) when no driver."""
    if not os.path.isfile(GECKODRIVER_BIN):
        pytest.fail(_NO_DRIVER_MSG)
    return GECKODRIVER_BIN


# --------------------------------------------------------------------------
# A. Structural tests
# --------------------------------------------------------------------------

def _skill_path(name):
    return os.path.join(AGENTS_DIR, name, "SKILL.md")


def test_a1_frontmatter_browser_tester():
    content = open(_skill_path("browser-tester")).read()
    assert content.startswith("---")
    assert "name: browser-tester" in content
    assert "description:" in content
    assert "version:" in content
    assert "model: workhorse" in content


def test_a2_verdict_contract_present():
    content = open(_skill_path("browser-tester")).read()
    assert "---VERDICT---" in content
    assert "---END---" in content
    assert "blocking_count" in content
    assert "status: PASS | FAIL | BLOCKED" in content


def test_a3_execute_only_no_write_instructions():
    content = open(_skill_path("browser-tester")).read()
    # must NOT tell the agent to modify/create source files
    for forbidden in ("create, modify, or delete files", "write_file", "patch the code"):
        assert forbidden not in content
    assert "execute-only" in content.lower() or "execute only" in content.lower()


def test_a4_visual_tester_documents_vision_requirement():
    content = open(_skill_path("visual-tester")).read()
    assert "vision" in content.lower()
    assert "NOT OPERABLE" in content
    assert "no vision" in content.lower()


def test_a5_scripts_exist_and_compile():
    for script in ("smoke_run.py", "webdriver_client.py", "setup-browser-testing.sh"):
        path = os.path.join(BIN_DIR, script)
        assert os.path.exists(path), f"{script} missing"
    subprocess.run([sys.executable, "-m", "py_compile", os.path.join(BIN_DIR, "smoke_run.py")], check=True)
    subprocess.run([sys.executable, "-m", "py_compile", os.path.join(BIN_DIR, "webdriver_client.py")], check=True)
    # shell syntax
    subprocess.run(["bash", "-n", os.path.join(BIN_DIR, "setup-browser-testing.sh")], check=True)


# --------------------------------------------------------------------------
# B. Behavioral tests (require geckodriver + Firefox)
# --------------------------------------------------------------------------
# These tests ERROR loudly (never silently skip) when geckodriver is
# unavailable — see _require_driver() at the top of the module. A silent
# "5 passed, 3 skipped" would hide the behavioral suite; the environment
# must either provide the driver or state why it can't.
# Set GECKODRIVER_BIN to the driver path (see docs/browser-smoke-testing.md).


@pytest.fixture(scope="module")
def fixture_server():
    """Start the smoke fixture app on an ephemeral port."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([sys.executable, FIXTURE, str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                break
        except Exception:
            time.sleep(0.3)
    yield url
    proc.terminate()
    proc.wait(timeout=5)


def _run_smoke(url, name, extra=None, out_dir=None, screenshot_dir=None, env_extra=None, checks="page-load,dom-element"):
    cmd = [
        sys.executable, os.path.join(BIN_DIR, "smoke_run.py"),
        "--url", url, "--checks", checks, "--name", name,
        "--out-dir", out_dir or os.path.join(REPO, "reports", "test-smoke"),
        "--screenshots-dir", screenshot_dir or os.path.join(REPO, "reports", "test-smoke", "shots"),
    ]
    if extra:
        cmd.extend(extra)
    env = dict(os.environ)
    env["GECKODRIVER_BIN"] = GECKODRIVER_BIN
    env.update(env_extra or {})
    before = set(p for p in subprocess.check_output(["pgrep", "geckodriver"], text=True).split() if p) if shutil.which("pgrep") else set()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
    after = set(p for p in subprocess.check_output(["pgrep", "geckodriver"], text=True).split() if p) if shutil.which("pgrep") else set()
    return proc, (before, after)


def test_b1_pass_run(fixture_server, tmp_path):
    _require_driver()
    out = tmp_path / "out"
    shots = tmp_path / "shots"
    proc, _ = _run_smoke(fixture_server, "b1", out_dir=str(out), screenshot_dir=str(shots))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "status: PASS" in proc.stdout
    report = json.load(open(out / "b1.json"))
    assert report["verdict"] == "PASS"
    assert report["blocking_count"] == 0
    names = {c["check"] for c in report["checks"]}
    assert "title-nonempty" in names and "h1-present" in names


def test_b2_fail_run_with_screenshot(fixture_server, tmp_path):
    _require_driver()
    out = tmp_path / "out2"
    shots = tmp_path / "shots2"
    expect = '{"css":"#status","text":"NEVER-MATCHES"}'
    proc, _ = _run_smoke(fixture_server, "b2", extra=["--expect", expect],
                         out_dir=str(out), screenshot_dir=str(shots))
    assert proc.returncode == 1
    assert "status: FAIL" in proc.stdout
    report = json.load(open(out / "b2.json"))
    assert report["verdict"] == "FAIL"
    assert report["blocking_count"] >= 1
    assert any(c["status"] == "FAIL" for c in report["checks"])
    # failure screenshot written
    shot = os.path.join(str(shots), "b2-fail.png")
    assert os.path.exists(shot) and os.path.getsize(shot) > 0


def test_b3_no_leaked_driver(fixture_server, tmp_path):
    """After a run, the geckodriver processes the runner spawned are gone."""
    _require_driver()
    proc, (before, after) = _run_smoke(fixture_server, "b3", out_dir=str(tmp_path / "o3"), screenshot_dir=str(tmp_path / "s3"))
    assert proc.returncode == 0
    # any geckodriver that existed before must still exist; none NEW should remain
    new = after - before
    assert not new, f"leaked geckodriver processes: {new}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))