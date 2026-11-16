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

Running single test

```
 uv run pytest tests/playwright/test_todos.py::test_http_method_post_create
```

Generate report

```
uv run pytest tests/playwright --html=reports/playwright-report.html --self-contained-html
```

Parallel execution

```
uv run pytest tests/playwright -n 4
```
