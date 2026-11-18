# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import plistlib

import pytest

from mvt.ios.modules.mixed.applications import Applications


@pytest.fixture()
def applications_factory(tmp_path):
    def create(data):
        plist_path = tmp_path / "Info.plist"
        with plist_path.open("wb") as handle:
            plistlib.dump(data, handle, sort_keys=False)
        module = Applications(target_path=str(tmp_path))
        module.is_backup = True
        module.run()
        return module

    return create


def test_application_inventory_preserves_metadata_and_deduplicates(
    applications_factory,
):
    metadata = {
        "softwareVersionBundleId": "org.example.store",
        "name": "Example App",
        "sourceApp": "com.apple.AppStore",
        "bundleShortVersionString": "1.0",
        "com.apple.iTunesStore.downloadInfo": {"purchaseDate": "2026-01-01T12:00:00Z"},
    }
    module = applications_factory(
        {
            "Applications": {
                "org.example.store": {
                    "iTunesMetadata": plistlib.dumps(metadata),
                    "PlaceholderIcon": b"icon",
                },
                "org.example.dictionary_only": {},
            },
            "Installed Applications": [
                "org.example.store",
                "org.example.inventory_only",
                "org.example.inventory_only",
            ],
        }
    )

    assert [entry["softwareVersionBundleId"] for entry in module.results] == [
        "org.example.store",
        "org.example.dictionary_only",
        "org.example.inventory_only",
    ]
    store = module.results[0]
    assert all(store[key] == value for key, value in metadata.items())
    assert store["has_itunes_metadata"] is True
    assert store["isodate"] == "2026-01-01 12:00:00.000000"
    assert store["icon_sha256"] == hashlib.sha256(b"icon").hexdigest()
    module.check_indicators()
    module.to_timeline()
    assert module.alertstore.alerts == []
    assert len(module.timeline) == 1
    assert module.timeline[0]["timestamp"] == store["isodate"]


@pytest.mark.parametrize(
    "data",
    [
        {"Installed Applications": ["org.example.app"]},
        {"Applications": {"org.example.app": {}}},
        {"Applications": {"org.example.app": {"PlaceholderIcon": b"icon"}}},
    ],
)
def test_apps_without_metadata_have_no_warning_or_timeline(
    applications_factory, indicators_factory, data
):
    module = applications_factory(data)
    entry = module.results[0]
    assert entry["name"] == "org.example.app"
    assert entry["softwareVersionBundleId"] == "org.example.app"
    assert entry["has_itunes_metadata"] is False
    assert "sourceApp" not in entry
    assert "isodate" not in entry
    if (
        "Applications" in data
        and "PlaceholderIcon" in data["Applications"]["org.example.app"]
    ):
        assert entry["icon_sha256"] == hashlib.sha256(b"icon").hexdigest()

    module.indicators = indicators_factory()
    module.check_indicators()
    module.to_timeline()
    assert module.alertstore.alerts == []
    assert module.timeline == []


@pytest.mark.parametrize("ioc_type", ["app_ids", "processes"])
def test_inventory_only_app_is_checked_against_iocs(
    applications_factory, indicators_factory, ioc_type
):
    module = applications_factory({"Installed Applications": ["org.example.malware"]})
    module.indicators = indicators_factory(**{ioc_type: ["org.example.malware"]})

    module.check_indicators()

    assert len(module.alertstore.alerts) == 1
    alert = module.alertstore.alerts[0]
    assert alert.event["softwareVersionBundleId"] == "org.example.malware"
    assert alert.matched_indicator.value == "org.example.malware"


def test_metadata_without_bundle_id_uses_inventory_id(
    applications_factory, indicators_factory
):
    module = applications_factory(
        {
            "Applications": {
                "org.example.malware": {
                    "iTunesMetadata": plistlib.dumps({"name": "Example App"})
                }
            }
        }
    )
    assert module.results[0]["softwareVersionBundleId"] == "org.example.malware"
    assert module.results[0]["has_itunes_metadata"] is True
    module.indicators = indicators_factory(app_ids=["org.example.malware"])

    module.check_indicators()

    assert len(module.alertstore.alerts) == 1
    assert module.alertstore.alerts[0].matched_indicator.value == "org.example.malware"


def test_existing_installer_warning_is_preserved(applications_factory):
    module = applications_factory(
        {
            "Applications": {
                "org.example.app": {
                    "iTunesMetadata": plistlib.dumps(
                        {
                            "softwareVersionBundleId": "org.example.app",
                            "sourceApp": "org.example.installer",
                        }
                    )
                }
            }
        }
    )

    module.check_indicators()

    assert len(module.alertstore.alerts) == 1
    assert "not installed from the App Store or MDM" in (
        module.alertstore.alerts[0].message
    )


def test_backup_without_application_lists_has_empty_inventory(
    applications_factory,
):
    assert applications_factory({}).results == []
