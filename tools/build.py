"""Package only the extension files; no dependency download or bundler needed."""

import json
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extension"


def build(destination: Path, *, fixture_origin: str | None = None) -> Path:
    manifest = json.loads((EXTENSION / "manifest.json").read_text())
    # Include only files referenced by the manifest, plus the distribution license.
    # Stray editor files or development material cannot enter a release archive.
    runtime_paths = set(manifest.get("icons", {}).values())
    for script in manifest.get("content_scripts", []):
        runtime_paths.update(script.get("js", []))
        runtime_paths.update(script.get("css", []))
    if fixture_origin:
        # Local permission exists only in this temporary test archive.
        origin = urlsplit(fixture_origin)
        pattern = f"{origin.scheme}://{origin.hostname}/*"
        manifest["host_permissions"].append(pattern)
        manifest["content_scripts"][0]["matches"].append(pattern)
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = {
        "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode(),
        "LICENSE": (ROOT / "LICENSE").read_bytes(),
    }
    for relative in runtime_paths:
        source = EXTENSION / relative
        if not source.resolve().is_relative_to(EXTENSION.resolve()):
            raise ValueError(f"Extension resource is outside extension/: {relative}")
        files[relative] = source.read_bytes()
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    return destination


if __name__ == "__main__":
    version = json.loads((EXTENSION / "manifest.json").read_text())["version"]
    release = build(ROOT / "dist" / f"youtube-fitscreen-{version}.xpi")
    digest = hashlib.sha256(release.read_bytes()).hexdigest()
    release.with_suffix(".xpi.sha256").write_text(f"{digest}  {release.name}\n")
    # Preserve the development filename used in earlier versions of this project.
    (ROOT / "dist" / "youtube-fitscreen.xpi").write_bytes(release.read_bytes())
    print(release)
