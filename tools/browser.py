"""Shared Selenium setup for the installed Zen/Firefox browser and geckodriver."""

import os
import shutil
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

ROOT = Path(__file__).resolve().parents[1]


def start_browser(*, headless: bool = False, log_name: str = "geckodriver.log"):
    binary = os.environ.get("BROWSER_BINARY") or os.environ.get("ZEN_BINARY")
    if not binary:
        # Arch's zen-browser command is a wrapper; geckodriver needs the ELF binary.
        candidates = ["/opt/zen-browser-bin/zen-bin", "/opt/zen-browser/zen-bin"]
        binary = next((path for path in candidates if Path(path).is_file()), None)
        binary = binary or shutil.which("zen-browser") or shutil.which("zen")
    geckodriver = shutil.which("geckodriver")
    if not binary or not geckodriver:
        raise RuntimeError("Install Zen/Firefox and geckodriver with yay; set BROWSER_BINARY to the browser executable.")
    if not headless and not os.environ.get("WAYLAND_DISPLAY"):
        raise RuntimeError("A Wayland session is required for headed testing. Use --headless otherwise.")

    options = Options()
    options.binary_location = binary
    options.add_argument("-no-remote")
    if headless:
        options.add_argument("-headless")
    options.set_preference("zen.welcome-screen.seen", True)
    options.set_preference("browser.shell.checkDefaultBrowser", False)
    options.set_preference("browser.aboutwelcome.enabled", False)
    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("media.autoplay.default", 0)
    options.set_preference("full-screen-api.transition-duration.enter", "0 0")
    options.set_preference("full-screen-api.transition-duration.leave", "0 0")
    options.set_preference("full-screen-api.warning.timeout", 0)
    environment = {**os.environ, "MOZ_ENABLE_WAYLAND": "1", "GDK_BACKEND": "wayland"}
    environment.pop("DISPLAY", None)
    if not headless:
        environment.pop("MOZ_HEADLESS", None)
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    service = Service(
        executable_path=geckodriver,
        log_output=str(artifacts / log_name),
        env=environment,
    )
    # An explicit driver path prevents Selenium Manager from downloading drivers.
    # geckodriver creates and removes an isolated temporary browser profile.
    driver = webdriver.Firefox(options=options, service=service)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(15)
    driver.set_window_size(1280, 800)
    return driver
