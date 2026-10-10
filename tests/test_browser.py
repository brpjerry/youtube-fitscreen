import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from tools.build import ROOT

BUTTON = ".ytf-button"
VIDEO = "video.html5-main-video"
PLAYER = ".html5-video-player"


def wait(driver, condition):
    return WebDriverWait(driver, 15).until(condition)


def open_player(driver, origin):
    driver.get(f"{origin}/player.html")
    wait(driver, lambda d: d.find_elements(By.CSS_SELECTOR, BUTTON))
    wait(driver, lambda d: d.execute_script("return document.querySelector('video').videoWidth > 0"))


def fullscreen(driver, *, shortcut=False):
    player = driver.find_element(By.CSS_SELECTOR, PLAYER)
    if shortcut:
        # YouTube hides its fullscreen button in narrow windows; its real keyboard
        # shortcut works there too (including under a tiling Wayland compositor).
        player.send_keys("f")
    else:
        ActionChains(driver).move_to_element(player).perform()
        control = driver.find_element(By.CSS_SELECTOR, ".ytp-fullscreen-button")
        wait(driver, lambda _: control.is_displayed())
        control.click()
    wait(driver, lambda d: d.execute_script("return !!document.fullscreenElement"))
    wait(driver, lambda d: d.find_element(By.CSS_SELECTOR, BUTTON).is_displayed())
    # Site icon padding must not push our icon into the adjacent control.
    assert driver.execute_script("""
        const button = document.querySelector('.ytf-button').getBoundingClientRect();
        const icon = document.querySelector('.ytf-button svg').getBoundingClientRect();
        return ['x', 'y', 'width', 'height'].every(key => Math.abs(icon[key] - button[key]) < 1);
    """)


def cropped(driver):
    return driver.execute_script(
        "return document.querySelector(arguments[0]).classList.contains('ytf-crop') && "
        "getComputedStyle(document.querySelector(arguments[1])).objectFit === 'cover'", PLAYER, VIDEO
    )


def assert_video_fills_player(driver):
    wait(driver, cropped)
    result = driver.execute_script("""
        const player = document.querySelector(arguments[0]).getBoundingClientRect();
        const video = document.querySelector(arguments[1]);
        const box = video.getBoundingClientRect();
        return {
            errors: ['x', 'y', 'width', 'height'].map(key => Math.abs(player[key] - box[key])),
            position: getComputedStyle(video).objectPosition,
            width: video.videoWidth, height: video.videoHeight
        };
    """, PLAYER, VIDEO)
    assert max(result["errors"]) < 2, result
    assert result["position"] == "50% 50%"
    assert result["width"] > 0 and result["height"] > 0


@pytest.mark.parametrize("dimensions", [(640, 480), (1280, 540), (360, 640)])
def test_crop_toggle_and_fullscreen_exit(driver, fixture_origin, dimensions):
    open_player(driver, fixture_origin)
    driver.execute_script("setVideoSize(...arguments)", *dimensions)
    wait(driver, lambda d: d.execute_script("return document.querySelector('video').videoWidth") == dimensions[0])
    button = driver.find_element(By.CSS_SELECTOR, BUTTON)
    assert not button.is_displayed()
    assert not cropped(driver)
    fullscreen(driver)
    assert button.get_attribute("aria-pressed") == "false"
    driver.save_screenshot(str(ROOT / "artifacts" / f"contain-{dimensions[0]}.png"))
    button.click()
    assert_video_fills_player(driver)
    assert button.get_attribute("aria-pressed") == "true"
    driver.save_screenshot(str(ROOT / "artifacts" / f"crop-{dimensions[0]}.png"))
    # YouTube can update its inline dimensions while crop mode is enabled.
    driver.execute_script("document.querySelector('video').style.width = '123px'")
    assert_video_fills_player(driver)
    button.click()
    wait(driver, lambda d: not cropped(d))
    assert driver.execute_script("return getComputedStyle(document.querySelector('video')).width") == "123px"
    driver.execute_script("layoutVideo()")
    button.click()
    driver.execute_script("document.exitFullscreen()")
    wait(driver, lambda d: not d.find_element(By.CSS_SELECTOR, BUTTON).is_displayed())
    assert not cropped(driver)
    fullscreen(driver)
    assert_video_fills_player(driver)


def test_choice_survives_reload_and_syncs_between_tabs(driver, fixture_origin):
    open_player(driver, fixture_origin)
    fullscreen(driver)
    driver.find_element(By.CSS_SELECTOR, BUTTON).click()
    assert_video_fills_player(driver)
    driver.refresh()
    wait(driver, lambda d: d.find_element(By.CSS_SELECTOR, BUTTON).get_attribute("aria-pressed") == "true")
    fullscreen(driver)
    assert_video_fills_player(driver)
    driver.execute_script("document.exitFullscreen()")
    first_tab = driver.current_window_handle
    driver.switch_to.new_window("tab")
    open_player(driver, fixture_origin)
    fullscreen(driver)
    assert_video_fills_player(driver)
    driver.find_element(By.CSS_SELECTOR, BUTTON).click()
    wait(driver, lambda d: not cropped(d))
    driver.close()
    driver.switch_to.window(first_tab)
    wait(driver, lambda d: d.find_element(By.CSS_SELECTOR, BUTTON).get_attribute("aria-pressed") == "false")
    fullscreen(driver)
    assert not cropped(driver)


def test_replaced_controls_video_and_player(driver, fixture_origin):
    open_player(driver, fixture_origin)
    fullscreen(driver)
    driver.find_element(By.CSS_SELECTOR, BUTTON).click()
    driver.execute_script("""
        const controls = document.querySelector('.ytp-right-controls');
        controls.replaceChildren();
        const full = document.createElement('button');
        full.className = 'ytp-button ytp-fullscreen-button';
        full.textContent = 'Fullscreen';
        const group = document.createElement('div');
        group.className = 'ytp-right-controls-right';
        group.append(full);
        controls.append(group);
        const video = document.querySelector('video');
        const replacement = video.cloneNode();
        replacement.srcObject = video.srcObject;
        video.replaceWith(replacement);
        replacement.play();
        document.dispatchEvent(new Event('yt-navigate-finish'));
    """)
    wait(driver, lambda d: len(d.find_elements(By.CSS_SELECTOR, BUTTON)) == 1)
    assert driver.find_element(By.CSS_SELECTOR, '.ytp-right-controls-right .ytf-button')
    wait(driver, lambda d: d.execute_script("return document.querySelector('video').videoWidth > 0"))
    assert_video_fills_player(driver)
    driver.find_element(By.CSS_SELECTOR, BUTTON).click()
    wait(driver, lambda d: not cropped(d))
    driver.execute_script("document.exitFullscreen()")
    wait(driver, lambda d: not d.execute_script("return !!document.fullscreenElement"))
    driver.execute_script("""
        const old = document.querySelector('.html5-video-player');
        const replacement = old.cloneNode(true);
        replacement.querySelector('.ytf-button').remove();
        old.replaceWith(replacement);
        replacement.querySelector('.ytp-fullscreen-button').onclick = () => replacement.requestFullscreen();
    """)
    wait(driver, lambda d: len(d.find_elements(By.CSS_SELECTOR, BUTTON)) == 1)
    fullscreen(driver)
    driver.find_element(By.CSS_SELECTOR, BUTTON).click()
    wait(driver, cropped)


def test_keyboard_accessible_toggle(driver, fixture_origin):
    open_player(driver, fixture_origin)
    fullscreen(driver)
    button = driver.find_element(By.CSS_SELECTOR, BUTTON)
    button.send_keys(Keys.ENTER)
    assert_video_fills_player(driver)
    assert button.get_attribute("aria-label") == "Show entire video"
    button.send_keys(Keys.SPACE)
    wait(driver, lambda d: not cropped(d))
    assert button.get_attribute("aria-label") == "Crop to fill screen"


def test_unrelated_fullscreen_does_not_enable_crop(driver, fixture_origin):
    open_player(driver, fixture_origin)
    fullscreen(driver)
    driver.find_element(By.CSS_SELECTOR, BUTTON).click()
    driver.execute_script("document.exitFullscreen()")
    wait(driver, lambda d: not d.execute_script("return !!document.fullscreenElement"))
    driver.execute_script("""
        const other = document.createElement('button');
        other.id = 'other';
        other.textContent = 'Other fullscreen element';
        other.onclick = () => other.requestFullscreen();
        document.body.append(other);
    """)
    driver.find_element(By.ID, "other").click()
    wait(driver, lambda d: d.execute_script("return document.fullscreenElement?.id === 'other'"))
    assert not cropped(driver)
    assert not driver.find_element(By.CSS_SELECTOR, BUTTON).is_displayed()


@pytest.mark.live
def test_live_youtube(driver, request):
    driver.get(request.config.getoption("--youtube-url"))
    # Accept neither tracking nor login prompts. Consent pages or anti-bot blocks
    # should fail visibly and leave evidence instead of silently skipping a test.
    wait(driver, lambda d: d.find_elements(By.CSS_SELECTOR, BUTTON))
    wait(driver, lambda d: d.execute_script("return document.querySelector('video')?.videoWidth > 0"))
    driver.execute_script("document.querySelector('video').muted = true")
    fullscreen(driver, shortcut=True)
    driver.execute_script("document.querySelector('video').pause()")
    original = driver.find_element(By.CSS_SELECTOR, VIDEO).rect
    button = driver.find_element(By.CSS_SELECTOR, BUTTON)
    button.click()
    assert_video_fills_player(driver)
    driver.save_screenshot(str(ROOT / "artifacts" / "youtube-cropped.png"))
    # YouTube may rebuild the controls while the screenshot is captured.
    driver.find_element(By.CSS_SELECTOR, BUTTON).click()
    wait(driver, lambda d: not cropped(d))
    # YouTube itself can use object-fit: cover on a letterboxed video element.
    # The off state must restore its original geometry, regardless of that style.
    wait(driver, lambda d: all(
        abs(d.find_element(By.CSS_SELECTOR, VIDEO).rect[key] - original[key]) < 2
        for key in ("x", "y", "width", "height")
    ))
    driver.save_screenshot(str(ROOT / "artifacts" / "youtube-original.png"))
    driver.execute_script("document.exitFullscreen()")
    wait(driver, lambda d: not d.find_element(By.CSS_SELECTOR, BUTTON).is_displayed())
