#!/usr/bin/env python3
"""smoke_run.py — run a browser smoke test against a URL and emit a verdict block.

The browser-tester skill's canonical invocation. Drives geckodriver + headless
Firefox through the stdlib WebDriver client, runs the requested check sets,
writes a structured report (JSON + markdown), screenshots failures, and always
cleans up the browser and driver processes (and the geckodriver process it
spawns when GECKODRIVER_BIN is provided).

Exit code: 0 = all checks passed, 1 = at least one FAIL, 2 = runner/tooling error.

Usage (see SKILL.md for the agent-facing contract):
  python3 smoke_run.py --url http://localhost:8000 \
      --checks "page-load,dom-element,console-errors" \
      --name "login page smoke" \
      --out-dir reports/smoke --screenshots-dir /tmp/agent-screenshots

Checks (comma-separated; each = a named check set):
  page-load       page navigates, title non-empty, h1 present, body renders
  dom-element     assert aria-label/text/id against --expect (JSON: {"css":"#x","text":"Hi","aria-label":"Close"})
  glance          URL + title + h1 + status text + body text length (no assertions)
  console-errors  browser console has no entries with level error/severe
  selenium-basics if selenium is importable: find h1 by CSS, read text (else skipped)
  all             the union of the above
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from webdriver_client import SmokeClient  # noqa: E402

def _default_geckodriver() -> str:
    """Locate geckodriver: PATH first, then standard install dirs.

    setup-browser-testing.sh installs to /usr/local/bin when writable, else
    ~/.local/bin -- honour both so an env-provisioned host works with no env
    vars. GECKODRIVER_BIN always wins when set.
    """
    on_path = shutil.which("geckodriver")
    if on_path:
        return on_path
    for candidate in ("/usr/local/bin/geckodriver",
                      os.path.expanduser("~/.local/bin/geckodriver")):
        if os.path.exists(candidate):
            return candidate
    return "/usr/local/bin/geckodriver"  # last resort; DriverProc raises a clear error


GECKODRIVER_BIN = os.environ.get("GECKODRIVER_BIN", _default_geckodriver())
GECKODRIVER_URL = os.environ.get("GECKODRIVER_URL", "http://127.0.0.1:4444")
DEFAULT_OUT_DIR = "reports/smoke"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                # any HTTP status means the driver is listening; 405 is normal
                # for GET requests to the root from geckodriver.
                _ = r.status
                return
        except urllib.error.HTTPError:
            return  # HTTP error response = driver is up and answering
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(0.5)
    raise RuntimeError(f"geckodriver not ready at {url} within {timeout}s: {last}")


class DriverProc:
    """Owns a geckodriver subprocess for the duration of a smoke run."""

    def __init__(self, bin_path, url):
        self.bin_path = bin_path
        self.url = url
        self.proc = None

    def __enter__(self):
        if not os.path.exists(self.bin_path):
            raise FileNotFoundError(
                f"geckodriver not found at {self.bin_path}. Run "
                "bin/setup-browser-testing.sh first (or set GECKODRIVER_BIN)."
            )
        port = _free_port()
        self.proc = subprocess.Popen(
            [self.bin_path, "--port", str(port), "--log", "warn"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        url = f"http://127.0.0.1:{port}"
        _wait_ready(url)
        return url

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


# ------------------------------------------------------------------ check sets

def c_page_load(c: SmokeClient, url: str, ctx: dict):
    results = []
    try:
        c.navigate(url)
    except Exception as e:  # noqa: BLE001
        return [("page-load", "FAIL", f"navigation error: {e}")]
    title = c.title()
    results.append(("title-nonempty", "PASS" if title.strip() else "FAIL", f"title={title!r}"))
    try:
        h1 = c.text_of(c.find("css selector", "h1"))
        results.append(("h1-present", "PASS" if h1.strip() else "FAIL", f"h1={h1!r}"))
    except Exception as e:  # noqa: BLE001
        results.append(("h1-present", "FAIL", f"{type(e).__name__}: {e}"))
    try:
        body = c.text_of(c.find("css selector", "body"))
        results.append(("body-renders", "PASS" if body.strip() else "FAIL", f"body-len={len(body)}"))
    except Exception as e:  # noqa: BLE001
        results.append(("body-renders", "FAIL", f"{type(e).__name__}: {e}"))
    return results


def c_dom_element(c: SmokeClient, url: str, ctx: dict):
    expect = ctx.get("expect")
    if not expect:
        return [("dom-element", "SKIP", "no --expect provided")]
    sel = expect.get("css") or (("#" + expect["id"]) if expect.get("id") else None)
    if not sel:
        return [("dom-element", "SKIP", "expected 'css' or 'id' in --expect")]
    try:
        el = c.find("css selector", sel)
    except Exception as e:  # noqa: BLE001
        return [("dom-element", "FAIL", f"element {sel!r} not found: {type(e).__name__}: {e}")]
    results = []
    if "text" in expect:
        try:
            got = c.text_of(el)
            results.append(
                ("dom-text", "PASS" if expect["text"] in got else "FAIL",
                 f"expected {expect['text']!r} in {got!r}")
            )
        except Exception as e:  # noqa: BLE001
            results.append(("dom-text", "FAIL", f"{type(e).__name__}: {e}"))
    if "aria-label" in expect:
        try:
            aria = c._request("GET", f"/session/{c.session_id}/element/{el}/attribute/aria-label")["value"]
            results.append(
                ("aria-label", "PASS" if aria == expect["aria-label"] else "FAIL",
                 f"expected {expect['aria-label']!r} got {aria!r}")
            )
        except Exception as e:  # noqa: BLE001
            results.append(("aria-label", "FAIL", f"{type(e).__name__}: {e}"))
    return results


def c_glance(c: SmokeClient, url: str, ctx: dict):
    try:
        c.navigate(url)
    except Exception as e:  # noqa: BLE001
        return [("glance", "FAIL", f"navigation error: {e}")]
    out = {
        "url": c.current_url(),
        "title": c.title(),
    }
    for sel in ("h1", "h2", "#status", "body"):
        try:
            out[sel] = c.text_of(c.find("css selector", sel))[:200]
        except Exception:  # noqa: BLE001
            out[sel] = None
    return [("glance", "PASS", json.dumps(out, ensure_ascii=False))]


def c_console_errors(c: SmokeClient, url: str, ctx: dict):
    # geckodriver 0.35 does NOT implement the W3C /log endpoint (405) and does
    # not forward page console.error to the driver stderr. Console capture is
    # therefore unavailable; report SKIP rather than a false PASS.
    # Enable when a driver that supports /log (e.g. a newer geckodriver or
    # chromedriver) is used.
    return [("console-errors", "SKIP",
             "unsupported: geckodriver 0.35 lacks the W3C /log endpoint")]


def c_selenium_basics(c: SmokeClient, url: str, ctx: dict):
    try:
        import selenium  # noqa: F401
    except ImportError:
        return [("selenium-basics", "SKIP", "selenium not installed")]
    try:
        c.navigate(url)
        h1 = c.text_of(c.find("css selector", "h1"))
        return [("selenium-basics", "PASS", f"h1 via css = {h1!r}")]
    except Exception as e:  # noqa: BLE001
        return [("selenium-basics", "FAIL", f"{type(e).__name__}: {e}")]


CHECK_SETS = {
    "page-load": [c_page_load],
    "dom-element": [c_dom_element],
    "glance": [c_glance],
    "console-errors": [c_console_errors],
    "selenium-basics": [c_selenium_basics],
    "all": [c_page_load, c_dom_element, c_console_errors, c_selenium_basics],
}
ALL_SET_NAMES = {s for names in CHECK_SETS.values() for s in names}


def build_plan(names: list[str]) -> list:
    plan = []
    for name in names:
        if name not in CHECK_SETS:
            raise SystemExit(f"unknown check set: {name!r} (valid: {', '.join(sorted(CHECK_SETS))})")
        for fn in CHECK_SETS[name]:
            if fn not in plan:
                plan.append(fn)
    return plan


def run_checks(c: SmokeClient, url: str, ctx: dict, plan: list) -> list:
    out = []
    for fn in plan:
        try:
            out.extend(fn(c, url, ctx))
        except Exception as e:  # noqa: BLE001
            out.append((fn.__name__, "FAIL", f"runner error: {type(e).__name__}: {e}"))
    return out


def write_report(out_dir: str, name: str, checks: list, verdict: str,
                 blocking: int, advisory: int, screenshot_paths: list, url: str):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for check, status, detail in checks:
        rows.append({"check": check, "status": status, "detail": detail})
    report = {
        "name": name,
        "url": url,
        "verdict": verdict,
        "blocking_count": blocking,
        "advisory_count": advisory,
        "screenshots": screenshot_paths,
        "checks": rows,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    json_path = os.path.join(out_dir, f"{name or 'smoke'}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    md_path = os.path.join(out_dir, f"{name or 'smoke'}.md")
    with open(md_path, "w") as f:
        f.write(f"# Smoke Report: {name}\n\n")
        f.write(f"- URL: `{url}`\n- Verdict: **{verdict}**\n- Blocking: {blocking}, Advisory: {advisory}\n\n")
        f.write("| check | status | detail |\n|---|---|---|\n")
        for check, status, detail in checks:
            safe = str(detail).replace("|", "\\|").replace("\n", " ")
            f.write(f"| {check} | {status} | {safe} |\n")
    return json_path, md_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Browser smoke test runner (geckodriver/Firefox)")
    ap.add_argument("--url", required=True, help="URL to smoke test")
    ap.add_argument("--checks", default="page-load",
                    help="comma-separated check sets (default: page-load)")
    ap.add_argument("--name", default="smoke", help="report name")
    ap.add_argument("--expect", default=None,
                    help='JSON for dom-element: {"css":"#x","text":"Hi","aria-label":"Close"}')
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="report output dir")
    ap.add_argument("--screenshots-dir", default="/tmp/agent-screenshots", help="screenshot dir")
    ap.add_argument("--headless", action="store_true", default=True)
    ap.add_argument("--no-headless", dest="headless", action="store_false")
    ap.add_argument("--no-driver", action="store_true",
                    help="assume geckodriver already running at GECKODRIVER_URL; don't spawn one")
    ap.add_argument("--page-load-timeout", type=float, default=30.0)
    args = ap.parse_args(argv)

    checks = [s.strip() for s in args.checks.split(",") if s.strip()]
    plan = build_plan(checks)
    expect = json.loads(args.expect) if args.expect else None

    screenshots_dir = args.screenshots_dir
    os.makedirs(screenshots_dir, exist_ok=True)

    driver_url = GECKODRIVER_URL
    driver = None
    if not args.no_driver:
        driver = DriverProc(GECKODRIVER_BIN, GECKODRIVER_URL)
        try:
            driver_url = driver.__enter__()
        except Exception:
            driver.__exit__(None, None, None)
            raise

    client = SmokeClient(driver_url, timeout=args.page_load_timeout + 5)
    results = []
    screenshot_paths = []
    ctx = {"expect": expect, "logs": []}
    try:
        client.new_session(headless=args.headless)
        client._request("POST", f"/session/{client.session_id}/timeouts",
                        {"implicit": 0, "pageLoad": int(args.page_load_timeout * 1000), "script": 30000})
        results = run_checks(client, args.url, ctx, plan)
        ctx["logs"] = client.console_log()

        # screenshot on any failure
        if any(s == "FAIL" for _, s, _ in results):
            shot = os.path.join(screenshots_dir, f"{args.name}-fail.png")
            try:
                screenshot_paths.append(client.screenshot(shot))
            except Exception as e:  # noqa: BLE001
                results.append(("screenshot-on-fail", "ADVISORY", f"{type(e).__name__}: {e}"))
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        results.append(("runner", "FAIL", f"{type(e).__name__}: {e}"))
    finally:
        try:
            client.quit()
        finally:
            if driver:
                driver.__exit__(None, None, None)

    blocking = sum(1 for _, s, _ in results if s == "FAIL")
    advisory = sum(1 for _, s, _ in results if s == "ADVISORY")
    skipped = sum(1 for _, s, _ in results if s == "SKIP")
    verdict = "PASS" if blocking == 0 and results else "FAIL"

    json_path, md_path = write_report(
        args.out_dir, args.name, results, verdict, blocking, advisory,
        screenshot_paths, args.url,
    )

    print(f"::smoke:: name={args.name}")
    print(f"::smoke:: url={args.url}")
    for check, status, detail in results:
        print(f"::smoke:: check={check} status={status} detail={detail}")
    print(f"::smoke:: blocking={blocking} advisory={advisory} skipped={skipped}")
    print(f"::smoke:: report_json={json_path}")
    print(f"::smoke:: report_md={md_path}")
    print("---VERDICT---")
    print(f"status: {verdict}")
    print(f"blocking_count: {blocking}")
    print(f"advisory_count: {advisory}")
    print(f"escalate: none")
    print(f"summary: browser smoke {verdict} — {blocking} blocking, {advisory} advisory, {skipped} skipped")
    print(f"findings:")
    for check, status, detail in results:
        if status in ("FAIL", "ADVISORY"):
            print(f"  - id: {check}")
            print(f"    severity: {'blocking' if status == 'FAIL' else 'advisory'}")
            print(f"    file: {args.url}")
            print(f"    line: 0")
            print(f"    problem: {detail[:200]}")
            print(f"    fix: inspect {md_path}")
    print("---END---")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())