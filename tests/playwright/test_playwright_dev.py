import re

from playwright.sync_api import (
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)
import pytest


def test_has_title(page: Page):
    page.goto("https://playwright.dev/python/")

    expect(page).to_have_title(re.compile("Playwright Python"))


def test_getting_started(page: Page):
    page.goto("https://playwright.dev/python/docs/writing-tests")

    link = page.locator('a[href="/python/docs/library"]')
    expect(link).to_be_visible()
    link.click()

    expect(page).to_have_url("https://playwright.dev/python/docs/library")


# ===========================================================================
# Beginner-Friendly Error Handling Examples
# ===========================================================================

def test_error_handling_element_not_found(page: Page):
    """Example 1: Catching a timeout when an element does not exist.

    Playwright waits for elements to appear before clicking. If an element
    cannot be found within the timeout, it raises PlaywrightTimeoutError.
    We can test and handle this using `pytest.raises(...)`.
    """
    page.goto("https://playwright.dev/python/")

    # Locate a button that does NOT exist on the page
    fake_button = page.locator("button#does-not-exist")

    # Expect a TimeoutError when attempting an action on a missing element
    with pytest.raises(PlaywrightTimeoutError):
        fake_button.click(timeout=1000)  # Wait 1 second (1000ms), then raise


def test_error_handling_optional_element(page: Page):
    """Example 2: Safely checking if an element exists without crashing.

    When dealing with elements that might not always be there (like banners or popups),
    use `is_visible()` to safely check without raising an error.
    """
    page.goto("https://playwright.dev/python/")

    # Check for a search button
    search_button = page.locator(".DocSearch-Button")

    # `is_visible()` returns True or False without raising an error
    if search_button.is_visible():
        assert search_button.is_enabled()
    else:
        # Gracefully handle the case when the element is absent
        assert not search_button.is_visible()


def test_error_handling_playwright_error_invalid_selector(page: Page):
    """Example 3: Catching PlaywrightError on invalid selector syntax.

    `PlaywrightError` is the base error class for Playwright exceptions.
    If a selector has malformed or illegal syntax (such as bad braces or quotes),
    Playwright immediately raises `PlaywrightError` without waiting for a timeout.
    """
    page.goto("https://playwright.dev/python/")

    # Malformed CSS selector with invalid characters
    bad_selector = page.locator("button:invalid-syntax{{}}")

    # Catch PlaywrightError using pytest.raises
    with pytest.raises(PlaywrightError) as exc_info:
        bad_selector.click()

    # The error message explains that the selector syntax is invalid
    assert "while parsing css selector" in str(exc_info.value)


def test_error_handling_playwright_error_network_failure(page: Page):
    """Example 4: Catching PlaywrightError on network navigation failure.

    When navigation fails (e.g., reaching a broken domain or network disconnect),
    `page.goto()` raises `PlaywrightError`.
    """
    with pytest.raises(PlaywrightError) as exc_info:
        page.goto("https://invalid-domain-xyz-12345.invalid")

    # The error message contains the underlying network error code
    assert "net::" in str(exc_info.value)
