#!/usr/bin/env python3
"""webdriver_client.py — minimal W3C WebDriver client (Python stdlib only).

Used by the browser-tester skill to drive geckodriver/Firefox for smoke tests
without any third-party dependency. Implements the small WebDriver surface the
check sets need: session, navigate, element find/text/click/clear/send_keys,
page timeout, console log, and screenshot.

The client mirrors the reference implementation validated in the prototype
(t_2a05f7c1): geometry-free, timeout-guarded, cleanup-first.

Design constraints (keep them):
  - stdlib only (urllib/json/base64) — the sandbox may not have pip/selenium.
  - Every request carries a timeout; every state-changing call is idempotent
    under errors so the caller's finally-quit always runs.
  - Element endpoints follow Selenium's "element-6066..." key convention so
    scripts that later switch to selenium keep the same shape.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request

GECKODRIVER_URL = os.environ.get("GECKODRIVER_URL", "http://127.0.0.1:4444")


class WebDriverError(RuntimeError):
    """A W3C WebDriver error response (HTTP >= 400 or empty reply)."""


class SessionExistsError(WebDriverError):
    """A session is already open on the driver; quit it before creating one."""


class ElementNotFoundError(WebDriverError):
    """Element lookup succeeded protocol-wise but returned no element."""


class TimeoutError(WebDriverError):
    """An explicit wait deadline expired."""


class SmokeClient:
    """Thin W3C WebDriver client for headless Firefox via geckodriver."""

    def __init__(self, base_url: str = GECKODRIVER_URL, timeout: float = 60.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session_id: str | None = None

    # ------------------------------------------------------------------ http
    def _request(self, method: str, path: str, body=None):
        url = f"{self.base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode())
            except Exception:
                payload = {}
            raise WebDriverError(f"HTTP {e.code} on {method} {path}: {payload}") from e
        except (urllib.error.URLError, ConnectionError, OSError, TimeoutError) as e:
            # Callers treat connection failures as fatal-with-cleanup; never loop.
            raise WebDriverError(f"driver unreachable on {method} {path}: {e}") from e

    def _element_id(self, payload) -> str:
        value = payload.get("value")
        if isinstance(value, dict):
            eid = value.get("element-6066-11e4-a52e-4f735466cecf") or value.get("ELEMENT")
            if eid:
                return str(eid)
        raise ElementNotFoundError(f"no element in response: {payload}")

    # ------------------------------------------------------------ lifecycle
    def new_session(self, headless: bool = True) -> str:
        caps = {
            "capabilities": {
                "alwaysMatch": {
                    "browserName": "firefox",
                    "moz:firefoxOptions": {
                        "args": ["-headless"] if headless else [],
                        # Capture browser console output; required for the
                        # console-errors check set to see page console.error.
                        "prefs": {"devtools.console.stdout.content": True},
                    },
                }
            }
        }
        try:
            result = self._request("POST", "/session", caps)
        except WebDriverError as e:
            if "already started" in str(e).lower() or "session not created" in str(e):
                raise SessionExistsError(
                    "a WebDriver session is already open; quit it first or reuse it"
                ) from e
            raise
        self.session_id = result["value"]["sessionId"]
        return self.session_id

    def quit(self) -> None:
        if self.session_id:
            try:
                self._request("DELETE", f"/session/{self.session_id}")
            except WebDriverError:
                pass
            self.session_id = None

    # ------------------------------------------------------------ navigation
    def navigate(self, url: str) -> None:
        self._request("POST", f"/session/{self.session_id}/url", {"url": url})

    def title(self) -> str:
        return self._request("GET", f"/session/{self.session_id}/title")["value"]

    def current_url(self) -> str:
        return self._request("GET", f"/session/{self.session_id}/url")["value"]

    # -------------------------------------------------------------- elements
    def find(self, using: str, value: str) -> str:
        result = self._request(
            "POST",
            f"/session/{self.session_id}/element",
            {"using": using, "value": value},
        )
        return self._element_id(result)

    def text_of(self, element_id: str) -> str:
        return self._request(
            "GET", f"/session/{self.session_id}/element/{element_id}/text"
        )["value"]

    def click(self, element_id: str) -> None:
        # Element endpoints require a JSON body; `{}` satisfies the decoder.
        self._request(
            "POST", f"/session/{self.session_id}/element/{element_id}/click", {}
        )

    def clear(self, element_id: str) -> None:
        self._request(
            "POST", f"/session/{self.session_id}/element/{element_id}/clear", {}
        )

    def send_keys(self, element_id: str, text: str) -> None:
        self._request(
            "POST",
            f"/session/{self.session_id}/element/{element_id}/value",
            {"text": text, "value": list(text)},
        )

    def tag_name(self, element_id: str) -> str:
        return self._request(
            "GET", f"/session/{self.session_id}/element/{element_id}/name"
        )["value"]

    # --------------------------------------------------------------- waiting
    def wait_for_text(self, using: str, value: str, expected: str,
                      timeout: float = 10.0) -> str:
        """Poll element text until it contains `expected`; return final text."""
        deadline = time.time() + timeout
        element_id = self.find(using, value)
        last = ""
        while time.time() < deadline:
            try:
                last = self.text_of(element_id)
            except WebDriverError:
                last = ""
            if expected in last:
                return last
            time.sleep(0.25)
        raise TimeoutError(
            f"timed out after {timeout:.0f}s waiting for {expected!r} in {value!r}; "
            f"last text: {last!r}"
        )

    # ------------------------------------------------------------ observability
    def screenshot(self, path: str) -> str:
        result = self._request("GET", f"/session/{self.session_id}/screenshot")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as f:
            f.write(base64.b64decode(result["value"]))
        return path

    def console_log(self) -> list:
        # geckodriver 0.35 does not implement the W3C /log endpoint; this is
        # intentionally best-effort and consumers must treat an empty list as
        # "unavailable", never as "no console errors".
        try:
            return self._request(
                "POST",
                f"/session/{self.session_id}/log",
                {"type": "browser"},
            ).get("value", [])
        except WebDriverError as e:
            return [{"level": "WARN", "message": f"log endpoint unavailable: {e}"}]


if __name__ == "__main__":
    # Self-check (used by tests/behavioral and by the skill's Verification step).
    import sys

    client = SmokeClient()
    try:
        sid = client.new_session(headless=True)
        client.navigate(os.environ.get("SMOKE_PAGE", "about:blank"))
        print("SMOKE-CLIENT-OK session=%s title=%r" % (sid, client.title()))
    finally:
        client.quit()
    sys.exit(0)