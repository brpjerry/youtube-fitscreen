# YouTube Fit Screen

A Firefox/Zen extension that adds a **Crop to fill screen** button next to YouTube's fullscreen button. Enter video fullscreen, then click the crop icon. A solid white center square means cropping is enabled; click again to show the entire frame.

The crop is centered and preserves proportions. Your choice is stored locally, shared between tabs, and reused for later videos. Exiting fullscreen restores YouTube's normal sizing. Captions and player controls are not enlarged. The extension works on desktop YouTube and YouTube's embedded players.

This fills the screen by cropping the video frame. It does not detect or remove black bars encoded into the video itself.

## Try it in your normal browser

1. Open `about:debugging#/runtime/this-firefox` in Zen or Firefox.
2. Select **Load Temporary Add-on…**, then select `extension/manifest.json` in this directory.
3. Open or refresh a YouTube video, enter fullscreen, and click the crop button beside the fullscreen control.

Temporary add-ons disappear when the browser restarts. The extension requests access only to YouTube and youtube-nocookie.com, plus local extension storage. It makes no network requests and collects no data.

## Browser automation on Arch / Wayland

Use the system packages:

```sh
yay -S --needed geckodriver python-selenium python-pytest
```

Zen must also be installed (`zen-browser-bin` on Arch). No pip packages, npm dependencies, browser downloads, X11, or Xvfb are needed. Selenium launches the installed Zen executable in a disposable profile with `MOZ_ENABLE_WAYLAND=1`, `GDK_BACKEND=wayland`, and no `DISPLAY` variable. Your normal browser profile is not used. `BROWSER_BINARY=/usr/bin/firefox` selects installed Firefox; `ZEN_BINARY=/absolute/path/to/zen-bin` remains supported for Zen.

Run commands below from this directory.

```sh
# Local regression tests in a visible Zen window.
python -m pytest -q

# Also exercise the production extension on real YouTube.
python -m pytest -q --live-youtube

# Choose a different public video for the live check.
python -m pytest -q --live-youtube --youtube-url 'https://www.youtube.com/watch?v=VIDEO_ID'

# Gecko headless mode, without a desktop session.
python -m pytest -q --headless
```

The local tests install a temporary copy of the extension with an additional localhost match. They use a generated video stream, real Fullscreen API interactions, and YouTube-shaped controls. They cover 4:3, ultrawide, and portrait video, toggling, leaving and re-entering fullscreen, reloading, cross-tab preference changes, replacing controls/video/player, and keyboard access. The production archive never includes localhost permissions.

The live check installs the production manifest without modification. It needs internet access and a playable video. Consent, login, regional restrictions, or bot challenges can block it; failures save evidence rather than silently passing. Screenshots, failure HTML, browser capabilities, and geckodriver logs are saved under `artifacts/` (ignored by Git).

## Drive Zen interactively

```sh
python -m tools.dev 'https://www.youtube.com/watch?v=aqz-KE-bpKQ'
```

This opens Zen with the extension installed and a Python console for direct browser inspection:

```python
driver.find_element(By.CSS_SELECTOR, '.html5-video-player').send_keys('f')
driver.find_element(By.CSS_SELECTOR, '.ytf-button').click()
driver.save_screenshot('artifacts/manual.png')
driver.execute_script("return getComputedStyle(document.querySelector('video')).objectFit")
reload_extension()  # Repackage edits, reinstall, and refresh the current page.
```

Use the browser normally alongside automation. Exit the console with Ctrl-D to close only this test session. Its temporary profile is removed. See [Selenium's Firefox documentation](https://www.selenium.dev/documentation/webdriver/browsers/firefox/) for the underlying API.

## Package

```sh
python -m tools.build
```

Creates a reproducible versioned release, `dist/youtube-fitscreen-0.1.0.xpi`, its SHA-256 checksum, and an identical development copy at `dist/youtube-fitscreen.xpi`. Packages contain the runtime files and license only. This is an unsigned archive; permanent installation in ordinary Firefox requires [Mozilla signing](https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/).

The extension uses a Manifest V3 content script and CSS, with no build step or background process. Its YouTube selectors are in `extension/content.js` and `extension/content.css`; if YouTube changes its player markup, run the live check when updating them.

Licensed under the [MIT License](LICENSE), copyright 2026 brpjerry.
