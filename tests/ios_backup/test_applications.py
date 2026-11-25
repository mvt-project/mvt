# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import plistlib
import time

import pytest

from mvt.ios.modules.mixed.applications import Applications


@pytest.fixture(params=["UTC", "Europe/Berlin", "America/New_York"])
def local_timezone(request, monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("Changing the local timezone requires time.tzset")

    with monkeypatch.context() as patch:
        patch.setenv("TZ", request.param)
        time.tzset()
        try:
            yield
        finally:
            patch.undo()
            time.tzset()


@pytest.mark.parametrize("acquisition", ["backup", "filesystem"])
@pytest.mark.parametrize(
    ("purchase_date", "expected"),
    [
        ("2026-01-01T12:00:00Z", "2026-01-01 12:00:00.000000"),
        ("2026-07-01T12:00:00Z", "2026-07-01 12:00:00.000000"),
    ],
)
def test_purchase_date_remains_utc(
    tmp_path, local_timezone, acquisition, purchase_date, expected
):
    metadata = {
        "softwareVersionBundleId": "org.example.app",
        "name": "Example App",
        "com.apple.iTunesStore.downloadInfo": {"purchaseDate": purchase_date},
    }
    module = Applications(target_path=str(tmp_path))
    if acquisition == "backup":
        info = {
            "Applications": {
                "org.example.app": {"iTunesMetadata": plistlib.dumps(metadata)}
            }
        }
        (tmp_path / "Info.plist").write_bytes(plistlib.dumps(info))
        module.is_backup = True
    else:
        app_dir = tmp_path / "private/var/containers/Bundle/Application/example"
        app_dir.mkdir(parents=True)
        (app_dir / "iTunesMetadata.plist").write_bytes(plistlib.dumps(metadata))
        module.is_fs_dump = True

    module.run()
    module.to_timeline()

    assert len(module.results) == 1
    assert module.results[0]["isodate"] == expected
    assert module.results[0]["com.apple.iTunesStore.downloadInfo"] == {
        "purchaseDate": purchase_date
    }
    assert len(module.timeline) == 1
    assert module.timeline[0]["timestamp"] == expected


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"com.apple.iTunesStore.downloadInfo": {}},
        {"com.apple.iTunesStore.downloadInfo": {"purchaseDate": ""}},
    ],
)
def test_missing_purchase_date_does_not_create_timestamp(metadata):
    module = Applications()

    module._parse_itunes_timestamp(metadata)

    assert "isodate" not in metadata
