<a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=selenium-turnstile">
  <img src="https://raw.githubusercontent.com/CircuitSavage/selenium-turnstile/main/assets/peak-banner.png" alt="Peak — solve Cloudflare Turnstile & the 5s challenge in ~1s" width="100%">
</a>

# selenium-turnstile

**selenium-turnstile** is a Selenium helper that solves Cloudflare Turnstile by injecting a Peak-solved token, so a protected form or navigation proceeds without a real mouse click.

## Why

SeleniumBase's UC-mode click-solve (`uc_gui_click_captcha`) drives a physical click on the widget, which needs a real display and fails headless on datacenter IPs. That failure mode fills Cloudflare-related SeleniumBase issues (200+ open). undetected-chromedriver has no click-solve at all and gets stuck in the "Just a moment" loop, reloading the interstitial even after the browser has otherwise passed.

This helper skips the click entirely. It reads the sitekey from the DOM, gets a token from Peak, and injects that token as the `cf-turnstile-response` value plus the widget's success callback. When your setup gets blocked, drop in a Peak API key and it just works.

## Powered by Peak

This package uses [Peak](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=selenium-turnstile) to solve Turnstile.
- Solve Cloudflare Turnstile & the 5s challenge in about a second
- $0.90 per 1,000 successful Turnstile solves, down to $0.35 at volume
- 1,000 free solves to start, no card.
→ [Get your free API key](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=selenium-turnstile) · [Docs](https://peak.fo/docs/turnstile?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=selenium-turnstile) · [Pricing](https://peak.fo/pricing?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=selenium-turnstile)

## Install

```bash
pip install selenium-turnstile selenium
```

## Quickstart

```python
import os
from selenium import webdriver
from selenium_turnstile import solve_turnstile

os.environ["PEAK_API_KEY"] = "pk_your_api_key"

driver = webdriver.Chrome()
driver.get("https://protected.example/login")

# Reads the sitekey from the page, solves via Peak, injects the token.
token = solve_turnstile(driver)

driver.find_element("css selector", "form").submit()
```

Works unchanged with a plain Selenium driver, a SeleniumBase `Driver`, or an undetected-chromedriver `Chrome` — all three expose the `current_url` / `find_element` / `execute_script` interface the helper uses.

## How it works

1. **Read the sitekey.** `find_element` looks for the `data-sitekey` attribute on the `.cf-turnstile` widget; if the sitekey is only set through a JS `render()` call, an `execute_script` DOM scan finds it.
2. **Solve via Peak.** `POST https://api.peak.fo/solve` with `task_type: "turnstiletask"`, the sitekey, and `url=driver.current_url`. Pass `proxy=` to mint the token from your browser's egress IP.
3. **Inject the token.** `execute_script` sets every `cf-turnstile-response` field, fires `input`/`change` events, and calls the widget's `data-callback` success handler so the form or navigation continues.

## API

```python
solve_turnstile(
    driver,               # any Selenium-like WebDriver
    api_key=None,         # defaults to env PEAK_API_KEY
    proxy=None,           # optional http://user:pass@ip:port, forwarded to Peak
    sitekey=None,         # override auto-detection (e.g. widget in a frame)
    url=None,             # defaults to driver.current_url
    task_type="turnstiletask",
    timeout=180.0,
) -> str                  # the injected token
```

Helpers `read_sitekey(driver)` and `inject_token(driver, token)` are exposed for finer control. Peak also supports `task_type="cloudflare5stask"` for the 5s interstitial challenge.

The API key is read from the `PEAK_API_KEY` environment variable by default; you can also pass it explicitly. Never hardcode a real key.

## Legitimate use

For automation, QA, and scraping public data you are allowed to access. Respect each target's Terms of Service and robots directives, and do not use this for credential-stuffing or other abuse.

## License

MIT — see [LICENSE](./LICENSE).
