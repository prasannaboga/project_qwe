https://playwright.dev/python/docs/intro

## Setup

pytest plugin

```
uv add pytest-playwright
```

Install the required browsers:

```
 uv run playwright install chromium
```

## Running tests

```
uv run pytest tests/playwright/test_playwright_dev.py -v -s
```

headed mode

```
uv run pytest tests/playwright/test_playwright_dev.py -v -s --headed
```

Debugging tests

```
PWDEBUG=1 uv run pytest tests/playwright/test_playwright_dev.py -v -s
```

Recording a trace

```
uv run pytest tests/playwright/test_playwright_dev.py -v -s --tracing on
```
