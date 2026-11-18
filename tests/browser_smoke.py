"""Exercise the Salmon Lines at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "salmonlines")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/salmonlines/")
                page.locator("#history").wait_for(state="visible")
                assert "Adams River" in page.locator("#title").inner_text()
                assert page.locator("#plot circle").count() > 0
                page.locator('[data-preset="yorkson"]').click()
                page.wait_for_function("document.querySelector('#title').textContent.includes('Yorkson')")
                assert page.locator("#metric").input_value() == "legacy"
                assert page.locator("#water").is_visible()
                page.locator("#compare-panel summary").click()
                page.locator("#compare-search").fill("Nathan Creek")
                page.locator("#compare").select_option("47988-31")
                page.wait_for_function("document.querySelectorAll('#legend .key').length === 2")
                assert "compare=47988-31" in page.url
                page.reload()
                page.wait_for_function("document.querySelectorAll('#legend .key').length === 2")
                page.locator("#records summary").click()
                assert page.locator("#table-body tr").count() > 25
                with page.expect_download() as exported:
                    page.locator("#export").click()
                assert exported.value.suggested_filename.endswith(".csv")
                page.locator("#search").fill("not-a-real-waterbody")
                assert "No matching" in page.locator("#matches").inner_text()
                page.locator('[data-preset="adams"]').click()
                page.wait_for_function("document.querySelector('#title').textContent.includes('Adams River')")
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: river search, chart, comparison, deep link, export and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
