import json
import struct
from zipfile import ZipFile

from tools.build import ROOT, build


def test_release_contains_only_extension_and_youtube_permissions(tmp_path):
    with ZipFile(build(tmp_path / "release.xpi")) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        icons = set(manifest["icons"].values())
        assert set(archive.namelist()) == {"manifest.json", "content.js", "content.css", "LICENSE"} | icons
        assert archive.read("LICENSE") == (ROOT / "LICENSE").read_bytes()
        for size, path in manifest["icons"].items():
            icon = archive.read(path)
            assert icon[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", icon[16:24]) == (int(size), int(size))
    expected = ["https://www.youtube.com/*", "https://www.youtube-nocookie.com/*"]
    assert manifest["host_permissions"] == expected
    assert manifest["content_scripts"][0]["matches"] == expected
    assert manifest["permissions"] == ["storage"]
    assert manifest["browser_specific_settings"]["gecko"]["data_collection_permissions"] == {"required": ["none"]}
    # This identity must remain stable once the first version is signed on AMO.
    assert manifest["browser_specific_settings"]["gecko"]["id"] == "{b592b1fa-7df4-40df-8089-d248ab55b9ea}"


def test_build_is_reproducible_and_fixture_permissions_do_not_leak(tmp_path):
    first = build(tmp_path / "first.xpi").read_bytes()
    with ZipFile(build(tmp_path / "fixture.xpi", fixture_origin="http://127.0.0.1:12345")) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert "http://127.0.0.1/*" in manifest["content_scripts"][0]["matches"]
    assert build(tmp_path / "second.xpi").read_bytes() == first
