# Browser Smoke Testing — Decision & Skill Documentation

**Date:** 2026-09-22 (AEST)
**Card:** t_2a05f7c1 — "Evaluate and Implement Browser Smoke Testing Agent Skill (geckodriver/Firefox)"
**Status:** Implemented (programmatic smoke testing); Visual Tester recorded as not-operable (pending vision model)

---

## 1. Decision

| Question | Decision | Rationale |
|---|---|---|
| Is a dedicated browser smoke-testing skill needed? | **YES** | No browser/DOM smoke-testing support existed in the agent roster (14 agents covered code quality, review, security, cost — nothing exercised a running web app). The task comment explicitly requested two new browser testing agents. |
| Browser Tester (programmatic, DOM/API/accessibility) | **IMPLEMENTED** | Environment supports it: Firefox 156.0 installed, geckodriver 0.35.0 provisioned, stdlib WebDriver client (no external deps). Verified live. |
| Visual Tester (vision, screenshot diff) | **RECORDED, NOT OPERABLE** | Requires a vision-capable model. Verified 2026-09-22: the LiteLLM catalog exposes only `local`, `workhorse`, `coding`, `reasoning` — **none support image input** (`/v1/models` → `image_url=False` for all; `vision_analyze` fails "No endpoints found that support image input"). The skill ships as an interface contract, `model: vision`, explicitly marked not-operable, with the exact enablement path. |

## 2. What was built

| Deliverable | Path | Purpose |
|---|---|---|
| Browser Tester skill | `agents/browser-tester/SKILL.md` | Agent skill: execute-only, verdict contract, geckodriver/Firefox smoke testing |
| Visual Tester skill | `agents/visual-tester/SKILL.md` | Vision-based visual regression (not-operable; interface contract) |
| Smoke runner | `bin/smoke_run.py` | Spawns geckodriver, runs check sets, emits verdict block, cleans up |
| WebDriver client | `bin/webdriver_client.py` | Minimal stdlib W3C WebDriver client (no pip/selenium dependency) |
| Env setup script | `bin/setup-browser-testing.sh` | One-time provisioner: geckodriver + venv (idempotent) |
| Fixture app | `tests/fixture/smoke_fixture.py` | HTTP fixture for validation/tests |
| Tests | `tests/test_browser_tester_skill.py` | Structural A-series + behavioral B-series (8 tests) |
| Dev Lead integration | `agents/dev-lead/SKILL.md` | W-BUILD steps 8.5 (Browser Tester) + 8.6 (Visual Tester, gated on vision model) |
| Installed skills | `/apps/hermes/.hermes/profiles/agent/skills/browser-tester/`, `.../visual-tester/` (active `agent` profile) | Live agent skill set |

## 3. Validation evidence

Prototype + full runs (all live, headless Firefox via geckodriver 0.35.0):

| Run | Checks | Result |
|---|---|---|
| Prototype (raw client loop) | session, navigate, title, heading, status, click, click-renders, screenshot | 8/8 PASS |
| `fixture-smoke` (runner, self-spawned driver) | page-load, dom-element, glance, console-errors, selenium-basics | PASS (console-errors + selenium-basics SKIP — see notes) |
| `fixture-smoke2` (deliberate wrong expectation) | dom-text NEV-ER-expect | FAIL, blocking_count=1, exit 1, failure screenshot written |
| Automated suite | A1-A5 structural + B1-B3 behavioral | **8/8 PASS** in 6.6s (`GECKODRIVER_BIN=/tmp/gecko-dl/geckodriver pytest -q tests/`) |

Cleanup verified: each run's driver and Firefox processes terminate (B3 test asserts no leaked geckodriver; `pgrep` after runs shows only pre-existing unrelated processes).

## 4. How an agent invokes it

```bash
python3 bin/smoke_run.py --url http://localhost:8000 \
    --checks "page-load,dom-element,glance" \
    --name "login-page" \
    --expect '{"css":"#login-submit","text":"Sign in"}' \
    --out-dir reports/smoke --screenshots-dir /tmp/agent-screenshots
```

- Exit 0 = PASS, 1 = FAIL, 2 = tooling error
- Emits `---VERDICT---` block (PASS/FAIL/BLOCKED, blocking/advisory counts, findings)
- One-time env: `bash bin/setup-browser-testing.sh` (installs geckodriver + venv; no sudo needed)
- No manual browser/driver setup per run — the runner spawns and cleans up its own geckodriver and Firefox

**Where does the runner find geckodriver?** `$GECKODRIVER_BIN` wins, then `geckodriver` on `PATH`, then `/usr/local/bin/geckodriver` (where `bin/setup-browser-testing.sh` installs it). In a sandbox without sudo, point at the download:

```bash
export GECKODRIVER_BIN=/path/to/geckodriver   # e.g. /tmp/gecko-dl/geckodriver
```

## 5. Known limitations (recorded)

1. **Console capture unavailable under geckodriver 0.35** — the W3C `/log` endpoint is not implemented (verified 405) and page `console.error` is not forwarded to the driver stderr. The `console-errors` check set therefore returns **SKIP**, never a false PASS. Revisit when a driver with `/log` support is available.
2. **Visual Tester not operable** — no vision-capable model in the LiteLLM catalog (verified). See `agents/visual-tester/SKILL.md` "Status" for the enablement path (add a vision model group, set `model: vision`).
3. **Selenium optional** — pip is blocked in this sandbox; the stdlib client is the default path. `selenium-basics` check set SKIPs gracefully when selenium is absent.

## 6. Scope compliance

- No general-purpose browser automation framework built — just the minimal WebDriver surface the smoke checks need.
- Firefox/geckodriver only (as specified).
- No per-application smoke scenarios written (out of scope) — the checks are generic and parameterized by `--url`/`--expect`.
- No CI/CD integration (out of scope by card).