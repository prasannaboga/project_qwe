import re
from playwright.sync_api import Page, expect


def test_has_title(page: Page):
    page.goto("https://playwright.dev/python/")

    expect(page).to_have_title(re.compile("Playwright Python"))


def test_getting_started(page: Page):
    page.goto("https://playwright.dev/python/docs/writing-tests")

    link = page.locator('a[href="/python/docs/library"]')
    expect(link).to_be_visible()
    link.click()

    expect(page).to_have_url("https://playwright.dev/python/docs/library")
