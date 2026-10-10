"""Open an interactive Zen session with this extension temporarily installed."""

import argparse
import code
import tempfile
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tools.browser import start_browser
from tools.build import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="https://www.youtube.com/")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="youtube-fitscreen-dev-") as directory:
        addon = Path(directory) / "extension.xpi"
        driver = start_browser(log_name="dev-geckodriver.log")
        try:
            def reload_extension():
                driver.install_addon(str(build(addon)), temporary=True)
                driver.refresh()

            driver.install_addon(str(build(addon)), temporary=True)
            driver.get(args.url)
            code.interact(
                banner="Zen is ready. Use driver, By, WebDriverWait, or reload_extension().\n"
                       "Example: driver.save_screenshot('artifacts/manual.png')\n"
                       "Ctrl-D closes this test browser and removes its temporary profile.",
                local={"driver": driver, "By": By, "WebDriverWait": WebDriverWait,
                       "reload_extension": reload_extension},
            )
        finally:
            driver.quit()


if __name__ == "__main__":
    main()
