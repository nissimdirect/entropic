"""Browser smoke tests for Entropic web UI using Playwright.

Verifies the core UI loads and key elements are present.
Run with: pytest tests/test_browser_smoke.py -v
Requires: pip install playwright && playwright install chromium
Server must be running: python3 server.py (default port 8000)
"""

import pytest

# Skip all tests if playwright is not installed
pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright


SERVER_URL = "http://localhost:8000"


def _server_is_running() -> bool:
    """Check if Entropic server is accessible."""
    import urllib.request

    try:
        urllib.request.urlopen(SERVER_URL, timeout=2)
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def browser():
    """Launch browser for test module."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.mark.skipif(
    not _server_is_running(),
    reason=f"Entropic server not running at {SERVER_URL}",
)
class TestBrowserSmoke:
    """Smoke tests that verify the Entropic UI loads correctly."""

    def test_homepage_loads(self, page):
        """Main page loads without errors."""
        response = page.goto(SERVER_URL)
        assert response is not None
        assert response.status == 200

    def test_title_present(self, page):
        """Page has a title."""
        page.goto(SERVER_URL)
        title = page.title()
        assert title, "Page should have a title"

    def test_upload_area_exists(self, page):
        """Upload/drop zone is present on the page."""
        page.goto(SERVER_URL)
        # Look for file input or drop zone
        file_input = page.query_selector('input[type="file"]')
        drop_zone = page.query_selector(
            '[class*="drop"], [class*="upload"], [id*="drop"], [id*="upload"]'
        )
        assert file_input or drop_zone, "Upload area should exist"

    def test_effects_panel_exists(self, page):
        """Effects list/panel is present."""
        page.goto(SERVER_URL)
        # Look for effects-related elements
        effects = page.query_selector(
            '[class*="effect"], [id*="effect"], [class*="category"], [id*="category"]'
        )
        assert effects, "Effects panel should exist"

    def test_no_console_errors(self, page):
        """No JavaScript errors on page load."""
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(SERVER_URL)
        page.wait_for_load_state("networkidle")
        assert len(errors) == 0, f"Console errors found: {errors}"

    def test_static_assets_load(self, page):
        """CSS and JS files load successfully (no 404s)."""
        failed_requests = []

        def handle_response(response):
            if response.status >= 400 and (
                response.url.endswith(".css") or response.url.endswith(".js")
            ):
                failed_requests.append(f"{response.status}: {response.url}")

        page.on("response", handle_response)
        page.goto(SERVER_URL)
        page.wait_for_load_state("networkidle")
        assert len(failed_requests) == 0, f"Failed static assets: {failed_requests}"
