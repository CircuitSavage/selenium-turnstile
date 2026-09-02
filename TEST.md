# Testing

The suite mocks Peak's `/solve` HTTP response and uses a fake WebDriver, so it
needs neither a live Peak API key nor a real browser. Selenium is an optional
import, so the tests also run with Selenium not installed.

## What is covered

`tests/test_solver.py` drives `solve_turnstile()` against a `FakeDriver` that
exposes `current_url`, `find_element` (returns an element with a sample
`data-sitekey`), and `execute_script` (records every call). `PeakClient._post`
is patched to return `{"success": true, "data": {"token": "XXXX.TEST"}}`.

Assertions:
- Sitekey is read from the DOM (`find_element` is called).
- Peak is called exactly once with the correct body: `task_type=turnstiletask`,
  the sample `sitekey`, and `url` equal to `driver.current_url`; `proxy` is
  omitted when not supplied.
- The token is injected via `execute_script`, passed as the script argument,
  and the injection script sets `cf-turnstile-response`.
- `proxy=` is forwarded into the Peak body when provided.
- `api_key` falls back to the `PEAK_API_KEY` environment variable.
- Sitekey detection falls back to the `execute_script` DOM scan when
  `find_element` finds nothing.
- Missing sitekey, a Peak `success:false` response, and a missing API key each
  raise `PeakError`.

## Run

```bash
cd selenium-turnstile
python -m unittest discover -s tests -v
```

Python 3.12 = `python`. No third-party packages required.

## Observed output

```
$ python --version
Python 3.12.0

$ python -m unittest discover -s tests -v
test_api_key_from_env (test_solver.SolveTurnstileTests.test_api_key_from_env) ... ok
test_missing_sitekey_raises (test_solver.SolveTurnstileTests.test_missing_sitekey_raises) ... ok
test_no_api_key_raises (test_solver.SolveTurnstileTests.test_no_api_key_raises) ... ok
test_peak_failure_raises (test_solver.SolveTurnstileTests.test_peak_failure_raises) ... ok
test_proxy_forwarded_to_peak (test_solver.SolveTurnstileTests.test_proxy_forwarded_to_peak) ... ok
test_reads_sitekey_calls_peak_and_injects (test_solver.SolveTurnstileTests.test_reads_sitekey_calls_peak_and_injects) ... ok
test_sitekey_fallback_via_execute_script (test_solver.SolveTurnstileTests.test_sitekey_fallback_via_execute_script) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.008s

OK
```
