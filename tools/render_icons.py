"""Regenerate the checked-in PNG icons from the original SVG using librsvg."""

import shutil
import subprocess

from tools.build import ROOT


def main():
    renderer = shutil.which("rsvg-convert")
    if not renderer:
        raise SystemExit("Install the system renderer with: yay -S --needed librsvg")
    destination = ROOT / "extension" / "icons"
    destination.mkdir(parents=True, exist_ok=True)
    for size in (32, 48, 64, 96, 128):
        subprocess.run([
            renderer, "--width", str(size), "--height", str(size),
            "--output", str(destination / f"icon-{size}.png"), str(ROOT / "assets" / "icon.svg"),
        ], check=True)
    print(f"Rendered icons in {destination}")


if __name__ == "__main__":
    main()
