# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging

import pytest
from click.testing import CliRunner
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

from mvt.android.cli import cli as android_cli
from mvt.common.module import MVTModule
from mvt.ios.cli import cli as ios_cli
from mvt.schemas import (
    OUTPUT_SCHEMA_VERSION,
    GenericModuleOutput,
    MappingOutput,
    RecordListOutput,
    export_json_schemas,
    get_output_model,
    get_output_models,
    schema_bundle,
    validate_output,
)


class CountRecord(BaseModel):
    model_config = ConfigDict(strict=True)
    count: int


class CountOutput(RootModel[list[CountRecord]]):
    pass


class CountModule(MVTModule):
    output_model = CountOutput


def test_common_output_model_validates_without_changing_root_shape():
    assert validate_output(RecordListOutput, [{"name": "example", "size": 2}]) == [
        {"name": "example", "size": 2}
    ]
    assert validate_output(MappingOutput, {"global": {"enabled": "1"}}) == {
        "global": {"enabled": "1"}
    }


def test_module_model_is_used_when_loading_existing_output(tmp_path):
    path = tmp_path / "count.json"
    path.write_text('[{"count": 4}]', encoding="utf-8")

    module = CountModule.from_json(str(path), logging.getLogger(__name__))

    assert module.results == [{"count": 4}]


def test_invalid_module_output_is_not_written(tmp_path, caplog):
    module = CountModule(results_path=str(tmp_path), results=[{"count": "four"}])

    with caplog.at_level(logging.ERROR):
        module.save_to_json()

    assert not (tmp_path / "count_module.json").exists()
    assert "does not match schema CountOutput" in caplog.text


def test_invalid_existing_output_raises_validation_error(tmp_path):
    path = tmp_path / "count.json"
    path.write_text('[{"count": "four"}]', encoding="utf-8")

    with pytest.raises(ValidationError):
        CountModule.from_json(str(path), logging.getLogger(__name__))


@pytest.mark.parametrize("platform", ["ios", "android"])
def test_every_builtin_module_has_a_non_generic_output_model(platform):
    module_models = {
        name: model
        for name, model in get_output_models(platform).items()
        if name not in {"alerts", "info", "timeline", "urls"}
    }

    assert module_models
    assert GenericModuleOutput not in module_models.values()


def test_known_mapping_and_specific_models_are_registered():
    assert get_output_model("backup_info.json", "ios") is MappingOutput
    assert get_output_model("dumpsys_receivers", "android") is MappingOutput
    assert get_output_model("tombstones", "android").__name__ == "TombstoneCrashOutput"
    assert get_output_model("sms_detected.json", "ios").__name__ == "AlertResults"


def test_schema_bundle_has_stable_versioned_shape():
    bundle = schema_bundle("android")

    assert bundle["output_schema_version"] == OUTPUT_SCHEMA_VERSION
    assert bundle["platform"] == "android"
    assert bundle["schemas"]["urls"]["$schema"].endswith("2020-12/schema")
    assert bundle["schemas"]["urls"]["type"] == "array"
    assert bundle["schemas"]["info"]["additionalProperties"] is False
    assert bundle["schemas"]["dumpsys_receivers"]["type"] == "object"


def test_export_json_schemas_writes_one_file_per_registered_output(tmp_path):
    paths = export_json_schemas(tmp_path, "android")

    assert len(paths) == len(get_output_models("android"))
    assert json.loads((tmp_path / "info.schema.json").read_text())["title"] == (
        "RunInfo"
    )


@pytest.mark.parametrize(
    ("cli", "platform"), [(ios_cli, "ios"), (android_cli, "android")]
)
def test_schema_cli_prints_machine_readable_bundle(cli, platform):
    result = CliRunner().invoke(cli, ["schemas"])

    assert result.exit_code == 0
    assert json.loads(result.output)["platform"] == platform


def test_schema_cli_exports_schema_files(tmp_path):
    result = CliRunner().invoke(android_cli, ["schemas", "--output", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "urls.schema.json").exists()
