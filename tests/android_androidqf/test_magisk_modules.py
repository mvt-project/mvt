import json
import zipfile

from mvt.android.modules.androidqf import ANDROIDQF_MODULES
from mvt.android.modules.androidqf.magisk_modules import MagiskModules

from ..utils import list_files


def write_manifest(acquisition_path, modules, status="collected"):
    manifest_path = acquisition_path / "magisk_modules" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": status,
                "acquisition_method": "adb exec-out su -c cat",
                "modules": modules,
            }
        ),
        encoding="utf-8",
    )


def run_module_from_dir(module, acquisition_path):
    parent_path = acquisition_path.absolute().parent.as_posix()
    module.from_dir(parent_path, list_files(str(acquisition_path)))
    module.run()


def test_magisk_modules_registered():
    assert MagiskModules in ANDROIDQF_MODULES


def test_magisk_modules_parses_properties_and_state(tmp_path):
    acquisition_path = tmp_path / "androidqf"
    properties_path = acquisition_path / "magisk_modules" / "0000" / "module.prop"
    properties_path.parent.mkdir(parents=True)
    properties_path.write_text(
        "\n".join(
            [
                "# Example module",
                "id=example.module",
                "name=Example Module",
                "version=1.2.3",
                "versionCode=12",
                "author=Example Author",
                "description=Example=with an equals sign",
                "updateJson=https://example.invalid/update.json",
                "customKey=custom value",
                "malformed line",
            ]
        ),
        encoding="utf-8",
    )
    write_manifest(
        acquisition_path,
        [
            {
                "device_path": "/data/adb/modules/example.module",
                "directory_name": "example.module",
                "module_prop_path": "magisk_modules/0000/module.prop",
                "module_prop_status": "collected",
                "state_files": ["disable", "update"],
                "state_files_complete": True,
            }
        ],
    )

    module = MagiskModules()
    run_module_from_dir(module, acquisition_path)

    assert len(module.results) == 1
    result = module.results[0]
    assert result["id"] == "example.module"
    assert result["name"] == "Example Module"
    assert result["version"] == "1.2.3"
    assert result["version_code"] == "12"
    assert result["author"] == "Example Author"
    assert result["description"] == "Example=with an equals sign"
    assert result["update_json"] == "https://example.invalid/update.json"
    assert result["properties"]["customKey"] == "custom value"
    assert result["disabled"] is True
    assert result["removal_pending"] is False
    assert result["update_pending"] is True


def test_magisk_modules_preserves_unknown_state(tmp_path):
    acquisition_path = tmp_path / "androidqf"
    write_manifest(
        acquisition_path,
        [
            {
                "device_path": "/data/adb/modules/incomplete",
                "directory_name": "incomplete",
                "module_prop_status": "missing",
                "state_files": [],
                "state_files_complete": False,
            }
        ],
        status="partial",
    )

    module = MagiskModules()
    run_module_from_dir(module, acquisition_path)

    assert len(module.results) == 1
    assert module.results[0]["disabled"] is None
    assert module.results[0]["removal_pending"] is None
    assert module.results[0]["update_pending"] is None
    assert module.results[0]["properties"] == {}


def test_magisk_modules_rejects_unsafe_property_path(tmp_path):
    acquisition_path = tmp_path / "androidqf"
    acquisition_path.mkdir()
    (tmp_path / "secret").write_text("id=must-not-be-read", encoding="utf-8")
    write_manifest(
        acquisition_path,
        [
            {
                "device_path": "/data/adb/modules/unsafe",
                "directory_name": "unsafe",
                "module_prop_path": "../secret",
                "module_prop_status": "collected",
                "state_files": [],
                "state_files_complete": True,
            }
        ],
    )

    module = MagiskModules()
    run_module_from_dir(module, acquisition_path)

    assert len(module.results) == 1
    assert module.results[0]["id"] is None
    assert module.results[0]["properties"] == {}


def test_magisk_modules_parses_root_level_zip_entries(tmp_path):
    archive_path = tmp_path / "androidqf.zip"
    manifest = {
        "schema_version": 1,
        "status": "collected",
        "modules": [
            {
                "device_path": "/data/adb/modules/zipped",
                "directory_name": "zipped",
                "module_prop_path": "magisk_modules/0000/module.prop",
                "module_prop_status": "collected",
                "state_files": [],
                "state_files_complete": True,
            }
        ],
    }
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("magisk_modules/manifest.json", json.dumps(manifest))
        archive.writestr(
            "magisk_modules/0000/module.prop", "id=zipped\nname=Zipped Module\n"
        )

    with zipfile.ZipFile(archive_path) as archive:
        module = MagiskModules()
        module.from_zip(archive, archive.namelist())
        module.run()

    assert len(module.results) == 1
    assert module.results[0]["id"] == "zipped"
    assert module.results[0]["name"] == "Zipped Module"
