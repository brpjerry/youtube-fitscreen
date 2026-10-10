"""Capture unedited screenshots of the production extension on live YouTube."""

import argparse
import os
import tempfile
from pathlib import Path

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from tools.browser import start_browser
from tools.build import ROOT, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="Capture at AMO's recommended 1280 × 800 size")
    args = parser.parse_args()
    if args.headless:
        os.environ["MOZ_HEADLESS_WIDTH"] = "1280"
        os.environ["MOZ_HEADLESS_HEIGHT"] = "800"
    output = ROOT / "store" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="youtube-fitscreen-screenshots-") as directory:
        addon = build(Path(directory) / "extension.xpi")
        driver = start_browser(headless=args.headless, log_name="store-screenshots.log")
        wait = WebDriverWait(driver, 30)
        try:
            driver.install_addon(str(addon), temporary=True)
            driver.get("https://www.youtube.com/watch?v=aqz-KE-bpKQ&themeRefresh=1")
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".ytf-button"))
            wait.until(lambda d: d.execute_script("return document.querySelector('video')?.readyState >= 2"))
            driver.execute_script("""
                const video = document.querySelector('video');
                video.muted = true;
                video.pause();
                video.currentTime = 30;
            """)
            wait.until(lambda d: d.execute_script("""
                const video = document.querySelector('video');
                return !video.seeking && video.readyState >= 2 && Math.abs(video.currentTime - 30) < 1;
            """))
            driver.find_element(By.CSS_SELECTOR, ".html5-video-player").send_keys("f")
            wait.until(lambda d: d.execute_script("return !!document.fullscreenElement"))
            wait.until(lambda d: d.find_element(By.CSS_SELECTOR, ".ytf-button").is_displayed())

            def capture(name):
                button = driver.find_element(By.CSS_SELECTOR, ".ytf-button")
                ActionChains(driver).move_to_element(button).perform()
                # Wait for two painted frames after style/layout changes.
                driver.execute_async_script("""
                    const done = arguments[0];
                    requestAnimationFrame(() => requestAnimationFrame(done));
                """)
                driver.save_screenshot(str(output / name))

            capture("01-entire-frame.png")
            driver.find_element(By.CSS_SELECTOR, ".ytf-button").click()
            wait.until(lambda d: d.find_element(By.CSS_SELECTOR, ".ytf-button").get_attribute("aria-pressed") == "true")
            capture("02-crop-to-fill.png")
            print(f"Saved store screenshots to {output}")
        finally:
            driver.quit()


if __name__ == "__main__":
    main()
