"""Solve a Turnstile-protected page with Selenium + Peak.

Run:
    pip install selenium selenium-turnstile
    export PEAK_API_KEY=pk_your_api_key
    python examples/solve_login.py

Works the same with a plain Selenium Chrome/Firefox driver, a
SeleniumBase ``Driver``, or an undetected-chromedriver ``Chrome`` -- they
all expose the ``current_url`` / ``find_element`` / ``execute_script``
interface that solve_turnstile needs.
"""

import os

from selenium import webdriver

from selenium_turnstile import solve_turnstile

TARGET = "https://protected.example/login"


def main():
    api_key = os.environ.get("PEAK_API_KEY", "pk_your_api_key")

    driver = webdriver.Chrome()
    try:
        driver.get(TARGET)

        # Optional: route the solve through the same proxy as the browser so
        # the token is minted from your egress IP.
        # proxy = "http://user:pass@ip:port"
        token = solve_turnstile(driver, api_key=api_key, proxy=None)
        print("Injected Turnstile token:", token[:24], "...")

        # The hidden cf-turnstile-response field is now set and the widget's
        # success callback has fired. Submit the form / continue navigation.
        driver.find_element("css selector", "form").submit()
        print("Now on:", driver.current_url)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
