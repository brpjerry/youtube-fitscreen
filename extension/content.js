(() => {
  "use strict";

  const FULLSCREEN_CLASS = "ytf-fullscreen";
  const CROP_CLASS = "ytf-crop";
  const players = new Map();
  let cropEnabled = false;
  let preferenceRevision = 0;
  let scheduled = false;

  function render(player, button) {
    const fullscreen = document.fullscreenElement;
    const active = Boolean(fullscreen && (fullscreen === player || fullscreen.contains(player)));
    player.classList.toggle(FULLSCREEN_CLASS, active);
    player.classList.toggle(CROP_CLASS, active && cropEnabled);
    const label = cropEnabled ? "Show entire video" : "Crop to fill screen";
    button.setAttribute("aria-label", label);
    button.setAttribute("aria-pressed", String(cropEnabled));
    button.title = label;
  }

  function renderAll() {
    for (const [player, button] of players) render(player, button);
  }

  function createButton() {
    const button = document.createElement("button");
    button.className = "ytp-button ytf-button";
    button.type = "button";
    const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icon.setAttribute("viewBox", "0 0 36 36");
    icon.setAttribute("aria-hidden", "true");
    const path = document.createElementNS(icon.namespaceURI, "path");
    path.setAttribute("d", "M13 8H8v5m15-5h5v5M8 23v5h5m15-5v5h-5");
    const square = document.createElementNS(icon.namespaceURI, "rect");
    square.setAttribute("class", "ytf-icon-square");
    square.setAttribute("x", "12");
    square.setAttribute("y", "12");
    square.setAttribute("width", "12");
    square.setAttribute("height", "12");
    icon.append(path, square);
    button.append(icon);
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      cropEnabled = !cropEnabled;
      preferenceRevision += 1;
      renderAll();
      browser.storage.local.set({cropEnabled}).catch((error) => {
        console.warn("YouTube Fit Screen could not save the crop preference:", error);
      });
    });
    // Keep YouTube's player shortcuts from also handling button activation.
    for (const type of ["keydown", "keyup"]) {
      button.addEventListener(type, (event) => {
        if (event.key === " " || event.key === "Enter") event.stopPropagation();
      });
    }
    return button;
  }

  function reconcile() {
    scheduled = false;
    for (const [player, button] of players) {
      if (!player.isConnected) {
        player.classList.remove(FULLSCREEN_CLASS, CROP_CLASS);
        button.remove();
        players.delete(player);
      }
    }
    for (const player of document.querySelectorAll(".html5-video-player")) {
      const fullscreenButton = player.querySelector(".ytp-fullscreen-button");
      // YouTube's newer controls nest the fullscreen button in an extra group.
      const controls = fullscreenButton?.parentElement || player.querySelector(".ytp-right-controls");
      if (!controls) continue;
      let button = players.get(player);
      if (!button) {
        button = createButton();
        players.set(player, button);
      }
      // YouTube replaces controls and players during same-page navigation.
      if (button.parentElement !== controls) {
        controls.insertBefore(button, fullscreenButton);
      }
      render(player, button);
    }
  }

  function scheduleReconcile() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(reconcile);
  }

  browser.storage.onChanged.addListener((changes, area) => {
    if (area !== "local" || !changes.cropEnabled) return;
    preferenceRevision += 1;
    cropEnabled = changes.cropEnabled.newValue === true;
    renderAll();
  });
  const initialRevision = preferenceRevision;
  browser.storage.local.get("cropEnabled").then((stored) => {
    // Don't overwrite a click or another tab's update with a stale startup read.
    if (initialRevision !== preferenceRevision) return;
    cropEnabled = stored.cropEnabled === true;
    renderAll();
  }).catch((error) => {
    console.warn("YouTube Fit Screen could not read the crop preference:", error);
  });

  document.addEventListener("fullscreenchange", reconcile);
  document.addEventListener("yt-navigate-finish", scheduleReconcile);
  new MutationObserver(scheduleReconcile).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
  reconcile();
})();
