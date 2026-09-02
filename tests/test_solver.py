"""Unit tests for selenium-turnstile.

These mock Peak's HTTP response and use a fake WebDriver, so they need
neither a live Peak key nor a real browser. Run with::

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

# Make the package importable when run from the repo root or tests/ dir.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from selenium_turnstile import PeakError, solve_turnstile  # noqa: E402
from selenium_turnstile.peak import PeakClient  # noqa: E402

SAMPLE_SITEKEY = "0x4AAAAAAADnPIDROzbs0Aaj"
SAMPLE_URL = "https://protected.example/login"
TEST_TOKEN = "XXXX.TEST"


class FakeElement:
    """Stands in for a Selenium WebElement carrying data-sitekey."""

    def __init__(self, sitekey):
        self._sitekey = sitekey

    def get_attribute(self, name):
        if name == "data-sitekey":
            return self._sitekey
        return None


class FakeDriver:
    """Minimal WebDriver double.

    Records every execute_script call so tests can assert the injection,
    and returns a sitekey-bearing element from find_element.
    """

    def __init__(self, sitekey=SAMPLE_SITEKEY, url=SAMPLE_URL):
        self.current_url = url
        self._sitekey = sitekey
        self.find_element_calls = []
        self.execute_script_calls = []

    def find_element(self, by, value):
        self.find_element_calls.append((by, value))
        if self._sitekey is None:
            raise RuntimeError("no such element")
        return FakeElement(self._sitekey)

    def execute_script(self, script, *args):
        self.execute_script_calls.append((script, args))
        # The sitekey-scan fallback expects a return value; injection ignores it.
        if "querySelector('[data-sitekey]')" in script:
            return self._sitekey
        return True


def _peak_success(*_args, **_kwargs):
    return {"success": True, "data": {"token": TEST_TOKEN}, "cost": 0.001}


class SolveTurnstileTests(unittest.TestCase):
    def test_reads_sitekey_calls_peak_and_injects(self):
        driver = FakeDriver()
        with mock.patch.object(PeakClient, "_post", side_effect=_peak_success) as post:
            token = solve_turnstile(driver, api_key="pk_test_key")

        # Token returned unchanged from the mocked Peak response.
        self.assertEqual(token, TEST_TOKEN)

        # Sitekey was read from the DOM via find_element.
        self.assertTrue(driver.find_element_calls)

        # Peak was called exactly once with the correct body.
        self.assertEqual(post.call_count, 1)
        payload = post.call_args.args[0]
        self.assertEqual(payload["task_type"], "turnstiletask")
        self.assertEqual(payload["sitekey"], SAMPLE_SITEKEY)
        self.assertEqual(payload["url"], SAMPLE_URL)
        self.assertNotIn("proxy", payload)  # omitted when not provided

        # Token was injected via execute_script, passed as the script arg.
        inject_calls = [
            c for c in driver.execute_script_calls if TEST_TOKEN in c[1]
        ]
        self.assertEqual(len(inject_calls), 1)
        script, args = inject_calls[0]
        self.assertIn("cf-turnstile-response", script)
        self.assertEqual(args, (TEST_TOKEN,))

    def test_proxy_forwarded_to_peak(self):
        driver = FakeDriver()
        proxy = "http://user:pass@1.2.3.4:8080"
        with mock.patch.object(PeakClient, "_post", side_effect=_peak_success) as post:
            solve_turnstile(driver, api_key="pk_test_key", proxy=proxy)
        payload = post.call_args.args[0]
        self.assertEqual(payload["proxy"], proxy)

    def test_api_key_from_env(self):
        driver = FakeDriver()
        with mock.patch.dict(os.environ, {"PEAK_API_KEY": "pk_env_key"}):
            with mock.patch.object(PeakClient, "_post", side_effect=_peak_success):
                token = solve_turnstile(driver)
        self.assertEqual(token, TEST_TOKEN)

    def test_sitekey_fallback_via_execute_script(self):
        # find_element finds nothing; the JS DOM scan supplies the sitekey.
        driver = FakeDriver(sitekey=None)
        driver._sitekey = None

        def exec_script(script, *args):
            driver.execute_script_calls.append((script, args))
            if "querySelector('[data-sitekey]')" in script:
                return SAMPLE_SITEKEY
            return True

        driver.execute_script = exec_script
        with mock.patch.object(PeakClient, "_post", side_effect=_peak_success) as post:
            token = solve_turnstile(driver, api_key="pk_test_key")
        self.assertEqual(token, TEST_TOKEN)
        self.assertEqual(post.call_args.args[0]["sitekey"], SAMPLE_SITEKEY)

    def test_missing_sitekey_raises(self):
        driver = FakeDriver(sitekey=None)
        driver.execute_script = lambda script, *args: None
        with self.assertRaises(PeakError):
            solve_turnstile(driver, api_key="pk_test_key")

    def test_peak_failure_raises(self):
        driver = FakeDriver()
        fail = {"success": False, "error": "insufficient balance"}
        with mock.patch.object(PeakClient, "_post", return_value=fail):
            with self.assertRaises(PeakError):
                solve_turnstile(driver, api_key="pk_test_key")

    def test_no_api_key_raises(self):
        driver = FakeDriver()
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PeakError):
                solve_turnstile(driver)


if __name__ == "__main__":
    unittest.main(verbosity=2)
