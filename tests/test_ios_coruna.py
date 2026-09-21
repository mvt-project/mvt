import hashlib
import json
import plistlib
import sqlite3

import pytest

from mvt.common.alerts import AlertLevel, AlertStore
from mvt.common.indicators import Indicators
from mvt.ios.coruna import (
    MAX_ARTIFACT_SIZE,
    alert_coruna_record,
    contained_regular_file,
    correlate_coruna_records,
    coruna_path_artifact,
    inspect_coruna_artifact,
)
from mvt.ios.modules.backup.manifest import Manifest
from mvt.ios.modules.fs.filesystem import Filesystem
from mvt.ios.paths import backup_device_path, check_ios_path

PHOTO = "/private/var/mobile/Library/Preferences/com.apple.0123456789abcdef.plist"
CONTAINER = "/private/var/mobile/Containers/Data/Application/12345678-1234-1234-1234-123456789abc"
PHOTO_DATA = {
    "LastProcessedFilePath": "/var/mobile/Media/DCIM/100APPLE/IMG_0001.PNG",
    "LastProcessedTimestamp": 1762537021.5,
}
CACHE_DATA = {
    "exp": "plasma",
    "ecid": "test-ecid",
    "gci": "test-gci",
    "unique-id": "test-id",
}


def indicators(**values):
    result = Indicators()
    result.ioc_collections.append(
        {"name": "test", "stix2_file_name": "test.stix2", **values}
    )
    return result


@pytest.mark.parametrize(
    "path", [PHOTO, PHOTO[1:], PHOTO.replace("/private", ""), PHOTO.replace("/", "\\")]
)
def test_photo_state_aliases(path):
    assert coruna_path_artifact(path) == {"kind": "photo-state"}


@pytest.mark.parametrize(
    "path",
    [
        PHOTO + ".bak",
        PHOTO.replace("abcdef", "abcdeg"),
        PHOTO.replace("abcdef", "abcde"),
        PHOTO.replace("/mobile/", "/root/"),
        "/tmp/" + PHOTO.rsplit("/", 1)[-1],
        CONTAINER + "/Library/.devcache",
        "/Documents/.devcache",
        CONTAINER.replace("/Data/", "/Bundle/") + "/Documents/.devcache",
    ],
)
def test_artifact_paths_are_scoped(path):
    assert coruna_path_artifact(path) is None


def test_backup_domain_scoping():
    relative = "Library/Preferences/" + PHOTO.rsplit("/", 1)[-1]
    assert coruna_path_artifact(relative, "HomeDomain")
    assert coruna_path_artifact(relative, "AppDomain-com.example.app") is None
    assert coruna_path_artifact("Documents/.devcache", "AppDomain-com.example.app")
    assert coruna_path_artifact("Documents/.devcache", "HomeDomain") is None
    assert (
        coruna_path_artifact("Documents/.devcache.bak", "AppDomain-com.example.app")
        is None
    )
    assert (
        backup_device_path("MediaDomain", "PostLogs.txt")
        == "/private/var/mobile/Media/PostLogs.txt"
    )
    assert (
        backup_device_path("CameraRollDomain", "Media/DCIM/image.png")
        == "/private/var/mobile/Media/DCIM/image.png"
    )
    assert backup_device_path("HomeDomain", "../root/file") is None
    assert backup_device_path("AppDomain-com.example.app", "Documents/file") is None


@pytest.mark.parametrize(
    "serializer",
    [
        plistlib.dumps,
        lambda d: plistlib.dumps(d, fmt=plistlib.FMT_BINARY),
        lambda d: json.dumps(d).encode(),
    ],
)
@pytest.mark.parametrize(
    "kind,data", [("photo-state", PHOTO_DATA), ("device-cache", CACHE_DATA)]
)
def test_content_formats(tmp_path, serializer, kind, data):
    path = tmp_path / "artifact"
    path.write_bytes(serializer(data))
    result = inspect_coruna_artifact(str(path), {"kind": kind})
    assert result["content_status"] == "matched"
    assert "test-ecid" not in json.dumps(result)
    assert "IMG_0001.PNG" not in json.dumps(result)


@pytest.mark.parametrize(
    "data",
    [
        {},
        [],
        {**PHOTO_DATA, "LastProcessedFilePath": "/tmp/photo"},
        {**PHOTO_DATA, "LastProcessedTimestamp": True},
        {**PHOTO_DATA, "LastProcessedTimestamp": float("inf")},
        {"lastProcessedTimestamp": 123},
    ],
)
def test_photo_content_requires_full_structure(tmp_path, data):
    path = tmp_path / "artifact"
    path.write_text(json.dumps(data))
    assert (
        inspect_coruna_artifact(str(path), {"kind": "photo-state"})["content_status"]
        == "unmatched"
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"not a plist",
        b"<?xml version='1.0'?><plist><broken",
        b"x" * (MAX_ARTIFACT_SIZE + 1),
    ],
    ids=["invalid", "malformed-xml", "oversized"],
)
def test_malformed_or_oversized_content(tmp_path, raw):
    path = tmp_path / "artifact"
    path.write_bytes(raw)
    assert (
        inspect_coruna_artifact(str(path), {"kind": "device-cache"})["content_status"]
        != "matched"
    )


@pytest.mark.parametrize(
    "data",
    [{**CACHE_DATA, "exp": "other"}, {"exp": "plasma"}, {**CACHE_DATA, "ecid": ""}],
)
def test_device_cache_content_requires_identifiers(tmp_path, data):
    path = tmp_path / "artifact"
    path.write_text(json.dumps(data))
    assert (
        inspect_coruna_artifact(str(path), {"kind": "device-cache"})["content_status"]
        == "unmatched"
    )


def test_correlation_requires_matching_identifiers_in_distinct_containers(tmp_path):
    path = tmp_path / "cache"
    path.write_text(json.dumps(CACHE_DATA))
    a = inspect_coruna_artifact(str(path), {"kind": "device-cache", "container": "one"})
    store = AlertStore()
    correlate_coruna_records([{"coruna_artifact": a}, {"coruna_artifact": a}], store)
    assert not store.alerts
    correlate_coruna_records(
        [{"coruna_artifact": a}, {"coruna_artifact": {**a, "container": "two"}}], store
    )
    assert len(store.alerts) == 1
    assert store.alerts[0].event["containers"] == ["one", "two"]
    assert store.alerts[0].level == AlertLevel.HIGH


def test_path_only_alert_is_medium():
    store = AlertStore()
    alert_coruna_record({"path": PHOTO, "isodate": "2026-09-15"}, store)
    assert store.alerts[0].level == AlertLevel.MEDIUM
    assert store.alerts[0].event_time == "2026-09-15"


@pytest.mark.parametrize(
    "ioc,path,expected",
    [
        ("/private/var/tmp/.ghost_upper", "/var/tmp/.ghost_upper/manifest.json", True),
        ("/var/tmp/ioslab_ctl", "private\\var\\tmp\\ioslab_ctl", True),
        ("/var/tmp/ioslab_ctl", "/var/tmp/ioslab_ctl2", False),
        ("/private/var/tmp/.ghost_upper/", "/var/tmp/.ghost_upper-copy/file", False),
    ],
)
def test_ios_path_iocs_respect_aliases_and_boundaries(ioc, path, expected):
    assert bool(check_ios_path(indicators(file_paths=[ioc]), path)) is expected


def test_filesystem_reads_candidate_and_hashes_when_requested(tmp_path):
    path = tmp_path / PHOTO.lstrip("/")
    path.parent.mkdir(parents=True)
    path.write_bytes(plistlib.dumps(PHOTO_DATA))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    module = Filesystem(
        target_path=str(tmp_path), module_options={"check_file_hashes": True}
    )
    module.indicators = indicators(files_sha256=[digest])
    module.run()
    module.check_indicators()
    assert sorted(a.level.value for a in module.alertstore.alerts) == [30, 40]
    record = next(r for r in module.results if "sha256" in r)
    replay = Filesystem(results=[record])
    replay.indicators = module.indicators
    replay.check_indicators()
    assert sorted(a.level.value for a in replay.alertstore.alerts) == [30, 40]


def test_filesystem_does_not_hash_by_default(tmp_path):
    (tmp_path / "file").write_bytes(b"example")
    module = Filesystem(target_path=str(tmp_path))
    module.run()
    assert all("sha256" not in r for r in module.results)


def test_backup_reads_coruna_candidate_and_maps_path_ioc(tmp_path):
    file_id = "a" * 40
    path = tmp_path / "aa" / file_id
    path.parent.mkdir()
    path.write_bytes(plistlib.dumps(PHOTO_DATA))
    with sqlite3.connect(tmp_path / "Manifest.db") as db:
        db.execute(
            "CREATE TABLE Files(fileID TEXT, domain TEXT, relativePath TEXT, flags INTEGER, file BLOB)"
        )
        db.execute(
            "INSERT INTO Files VALUES(?,?,?,?,?)",
            (
                file_id,
                "HomeDomain",
                "Library/Preferences/" + PHOTO.rsplit("/", 1)[-1],
                1,
                None,
            ),
        )
        db.execute(
            "INSERT INTO Files VALUES(?,?,?,?,?)",
            ("b" * 40, "MediaDomain", "PostLogs.txt", 1, None),
        )
    db.close()
    module = Manifest(
        target_path=str(tmp_path), module_options={"check_file_hashes": True}
    )
    module.indicators = indicators(
        file_paths=["/var/mobile/Media/PostLogs.txt"],
        files_sha256=[hashlib.sha256(path.read_bytes()).hexdigest()],
    )
    module.run()
    module.check_indicators()
    assert sorted(a.level.value for a in module.alertstore.alerts) == [30, 30, 40]


def test_acquisition_boundary(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"not evidence")
    assert not contained_regular_file(str(root), str(outside))


@pytest.mark.parametrize(
    "metadata", [{"flags": 2}, {"is_directory": True}, {"mode": 16877}]
)
def test_directories_are_not_coruna_file_artifacts(metadata):
    store = AlertStore()
    alert_coruna_record({"path": PHOTO, **metadata}, store)
    assert not store.alerts


def test_hash_option_reaches_ios_modules():
    from mvt.ios.cmd_check_backup import CmdIOSCheckBackup
    from mvt.ios.cmd_check_fs import CmdIOSCheckFS

    for command in (CmdIOSCheckBackup, CmdIOSCheckFS):
        assert command(hashes=True).module_options["check_file_hashes"]
