"""Solve Cloudflare Turnstile on a live Selenium page via the Peak API.

The flow is: read the Turnstile sitekey out of the DOM, ask Peak for a
token, then inject that token back into the page (hidden input + widget
success callback) so the form or navigation proceeds.

Selenium itself is an optional import. The functions accept any object
that quacks like a Selenium ``WebDriver`` (``current_url``,
``find_element``, ``execute_script``), which keeps them unit testable
without a real browser.
"""

from __future__ import annotations

import os
from typing import Optional

from .peak import DEFAULT_API_URL, TASK_TURNSTILE, PeakClient, PeakError

# CSS selectors that carry the Turnstile sitekey as a data attribute.
_SITEKEY_SELECTORS = (
    ".cf-turnstile[data-sitekey]",
    "[data-sitekey]",
    "div.cf-turnstile",
)

# JS that scans the DOM for a Turnstile sitekey. Used as a fallback when
# find_element does not turn one up (for example, sitekey configured only
# through the JS render() call).
_READ_SITEKEY_JS = r"""
var el = document.querySelector('[data-sitekey]');
if (el) { return el.getAttribute('data-sitekey'); }
var m = (document.documentElement.outerHTML || '').match(
    /(?:sitekey|render)\s*[:=]\s*["']((?:0x|1x)[^"']+)["']/i);
return m ? m[1] : null;
"""

# JS that injects a solved token. Sets every cf-turnstile-response field,
# fires input/change events so listeners react, and calls the widget's
# success callback (data-callback global, or window.turnstile internals).
_INJECT_TOKEN_JS = r"""
var token = arguments[0];
var fields = document.querySelectorAll(
    'input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"], ' +
    'input#cf-turnstile-response, [name="cf-turnstile-response"]');
if (!fields.length) {
    var holder = document.querySelector('.cf-turnstile') || document.body;
    var inp = document.createElement('input');
    inp.type = 'hidden';
    inp.name = 'cf-turnstile-response';
    holder.appendChild(inp);
    fields = [inp];
}
fields.forEach(function (f) {
    f.value = token;
    f.dispatchEvent(new Event('input', { bubbles: true }));
    f.dispatchEvent(new Event('change', { bubbles: true }));
});
var called = false;
document.querySelectorAll('[data-callback]').forEach(function (w) {
    var name = w.getAttribute('data-callback');
    if (name && typeof window[name] === 'function') {
        window[name](token);
        called = true;
    }
});
return called;
"""


def read_sitekey(driver) -> Optional[str]:
    """Return the Turnstile sitekey rendered on the current page, or None.

    Tries ``find_element`` against the widget's ``data-sitekey`` attribute
    first, then falls back to an ``execute_script`` DOM scan.
    """
    try:
        from selenium.webdriver.common.by import By

        css = By.CSS_SELECTOR
    except Exception:  # selenium not installed; use the raw locator string
        css = "css selector"

    for selector in _SITEKEY_SELECTORS:
        try:
            element = driver.find_element(css, selector)
        except Exception:
            continue
        if element is None:
            continue
        sitekey = element.get_attribute("data-sitekey")
        if sitekey:
            return sitekey.strip()

    sitekey = driver.execute_script(_READ_SITEKEY_JS)
    if sitekey:
        return str(sitekey).strip()
    return None


def inject_token(driver, token: str) -> None:
    """Inject a solved token into the page's Turnstile widget."""
    driver.execute_script(_INJECT_TOKEN_JS, token)


def solve_turnstile(
    driver,
    api_key: Optional[str] = None,
    proxy: Optional[str] = None,
    sitekey: Optional[str] = None,
    url: Optional[str] = None,
    task_type: str = TASK_TURNSTILE,
    api_url: Optional[str] = None,
    timeout: float = 180.0,
) -> str:
    """Solve the Turnstile challenge on ``driver``'s current page.

    Reads the sitekey from the DOM (unless ``sitekey`` is given), asks Peak
    for a token, injects it, and returns the token.

    ``api_key`` defaults to the ``PEAK_API_KEY`` environment variable.
    ``url`` defaults to ``driver.current_url``. ``proxy`` is forwarded to
    Peak so the token is minted from the same egress IP as the browser;
    omit it and Peak solves without one.

    Raises :class:`~selenium_turnstile.peak.PeakError` if no sitekey is
    found or Peak cannot solve the challenge.
    """
    api_key = api_key or os.environ.get("PEAK_API_KEY")

    if sitekey is None:
        sitekey = read_sitekey(driver)
    if not sitekey:
        raise PeakError(
            "No Turnstile sitekey found on the page. Pass sitekey= "
            "explicitly if the widget renders in a frame or after load."
        )

    if url is None:
        url = driver.current_url

    client = PeakClient(
        api_key,
        api_url=api_url or DEFAULT_API_URL,
        proxy=proxy,
        timeout=timeout,
    )
    token = client.solve(sitekey, url, proxy=proxy, task_type=task_type)
    inject_token(driver, token)
    return token
