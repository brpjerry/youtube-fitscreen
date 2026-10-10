import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from tools.browser import start_browser
from tools.build import ROOT, build


def pytest_addoption(parser):
    parser.addoption("--headless", action="store_true", help="Use Gecko headless instead of native Wayland")
    parser.addoption("--live-youtube", action="store_true", help="Also test a live YouTube video")
    parser.addoption("--youtube-url", default="https://www.youtube.com/watch?v=aqz-KE-bpKQ")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live-youtube"):
        for item in items:
            if "live" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Use --live-youtube to run against YouTube"))


@pytest.fixture(scope="session")
def fixture_origin():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    handler = functools.partial(QuietHandler, directory=str(ROOT / "tests" / "fixtures"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture(scope="session")
def browser(request):
    driver = start_browser(headless=request.config.getoption("--headless"))
    (ROOT / "artifacts" / "browser-capabilities.json").write_text(json.dumps(driver.capabilities, indent=2))
    yield driver
    driver.quit()


@pytest.fixture
def driver(browser, fixture_origin, tmp_path, request):
    live = "live" in request.node.keywords
    addon = build(tmp_path / "extension.xpi", fixture_origin=None if live else fixture_origin)
    addon_id = browser.install_addon(str(addon), temporary=True)
    yield browser
    # Capture before uninstalling or leaving fullscreen if an assertion failed.
    if getattr(request.node, "rep_call", None) and request.node.rep_call.failed:
        name = request.node.name.replace("/", "_")
        browser.save_screenshot(str(ROOT / "artifacts" / f"{name}.png"))
        (ROOT / "artifacts" / f"{name}.html").write_text(browser.page_source)
    browser.execute_script("if (document.fullscreenElement) document.exitFullscreen();")
    handles = browser.window_handles
    for handle in handles[1:]:
        browser.switch_to.window(handle)
        browser.close()
    browser.switch_to.window(handles[0])
    browser.get("about:blank")
    browser.uninstall_addon(addon_id)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())
