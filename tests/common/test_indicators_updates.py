import json
from types import SimpleNamespace

import pytest

from mvt.common import indicators, updates


@pytest.fixture
def updater_and_cache(tmp_path, monkeypatch):
    cache = tmp_path / "indicators"
    cache.mkdir()
    monkeypatch.setattr(updates, "MVT_DATA_FOLDER", str(tmp_path))
    monkeypatch.setattr(updates, "MVT_INDICATORS_FOLDER", str(cache))
    monkeypatch.setattr(indicators, "MVT_INDICATORS_FOLDER", str(cache))
    monkeypatch.setattr(indicators.settings, "STIX2", None)
    return updates.IndicatorsUpdates(), cache


def _mock_downloads(monkeypatch, updater, responses):
    monkeypatch.setattr(
        updater,
        "get_remote_index",
        lambda: {"indicators": [{"download_url": url} for url in responses]},
    )
    monkeypatch.setattr(updates.requests, "get", lambda url, *, timeout: responses[url])


def _bundle(domain):
    return json.dumps(
        {
            "objects": [
                {
                    "type": "indicator",
                    "id": "indicator--test",
                    "pattern": f"[domain-name:value = '{domain}']",
                }
            ]
        }
    )


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_refresh_retires_legacy_download(scheme, updater_and_cache, monkeypatch):
    updater, cache = updater_and_cache
    legacy = cache / "ools.example_iocs.stix2"
    legacy.write_text(_bundle("retired.example"), encoding="utf-8")
    unrelated = cache / "other.stix2"
    unrelated.write_text(_bundle("other.example"), encoding="utf-8")
    _mock_downloads(
        monkeypatch,
        updater,
        {
            f"{scheme}://tools.example/iocs.stix2": SimpleNamespace(
                status_code=200, text=_bundle("current.example")
            )
        },
    )

    updater.update()
    updater.update()

    assert not legacy.exists()
    assert (cache / "tools.example_iocs.stix2").is_file()
    loaded = indicators.Indicators()
    loaded.load_indicators_files([])
    assert {ioc.value for ioc in loaded.get_iocs("domains")} == {
        "current.example",
        "other.example",
    }


@pytest.mark.parametrize(
    ("other_host", "status_code", "expected_legacy"),
    [
        ("ools.example", 200, "other feed"),
        ("ools.example", 503, "cached feed"),
        ("stools.example", 503, "cached feed"),
        ("stools.example", 200, None),
    ],
)
def test_refresh_handles_legacy_filename_collisions(
    other_host, status_code, expected_legacy, updater_and_cache, monkeypatch
):
    updater, cache = updater_and_cache
    legacy = cache / "ools.example_iocs.stix2"
    legacy.write_text("cached feed", encoding="utf-8")
    _mock_downloads(
        monkeypatch,
        updater,
        {
            "https://tools.example/iocs.stix2": SimpleNamespace(
                status_code=200, text="refreshed feed"
            ),
            f"https://{other_host}/iocs.stix2": SimpleNamespace(
                status_code=status_code, text="other feed"
            ),
        },
    )

    updater.update()

    assert (cache / "tools.example_iocs.stix2").read_text(encoding="utf-8") == (
        "refreshed feed"
    )
    if expected_legacy is None:
        assert not legacy.exists()
    else:
        assert legacy.read_text(encoding="utf-8") == expected_legacy


@pytest.mark.parametrize("other_status", [200, 503])
def test_refresh_uses_filesystem_case_rules(
    updater_and_cache, monkeypatch, other_status
):
    updater, cache = updater_and_cache
    # These are the two paths the previous version wrote, in index order.
    legacy = cache / "ools.example_IOCs.stix2"
    other = cache / "ools.example_iocs.stix2"
    legacy.write_text(_bundle("retired.example"), encoding="utf-8")
    other.write_text(_bundle("cached-other.example"), encoding="utf-8")
    shared_file = legacy.samefile(other)
    _mock_downloads(
        monkeypatch,
        updater,
        {
            "https://tools.example/IOCs.stix2": SimpleNamespace(
                status_code=200, text=_bundle("current.example")
            ),
            "https://ools.example/iocs.stix2": SimpleNamespace(
                status_code=other_status, text=_bundle("updated-other.example")
            ),
        },
    )

    updater.update()

    assert legacy.exists() == shared_file
    loaded = indicators.Indicators()
    loaded.load_indicators_files([])
    assert {ioc.value for ioc in loaded.get_iocs("domains")} == {
        "current.example",
        "updated-other.example" if other_status == 200 else "cached-other.example",
    }
