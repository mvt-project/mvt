# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import pytest

from mvt.common.alerts import AlertStore
from mvt.common.module import MVTModule, run_module


@pytest.mark.parametrize("empty_results", [[], {}])
def test_saving_empty_module_output_removes_previous_files(tmp_path, empty_results):
    module = MVTModule(results_path=str(tmp_path), results=[{"previous": True}])
    module.alertstore.critical("Previous finding", "", module.results[0])
    module.save_to_json()
    results_path = tmp_path / "mvt_module.json"
    detections_path = tmp_path / "mvt_module_detected.json"
    assert results_path.is_file()
    assert detections_path.is_file()

    module.results = empty_results
    module.alertstore = AlertStore()
    module.save_to_json()

    assert not results_path.exists()
    assert not detections_path.exists()


@pytest.mark.parametrize("operation", [run_module, MVTModule.save_to_json])
@pytest.mark.parametrize("alias", [False, True])
def test_module_rejects_acquisition_directory_as_output(tmp_path, operation, alias):
    target = tmp_path / "acquisition"
    target.mkdir()
    source = target / "mvt_module.json"
    source.write_text('["source evidence"]')
    output = target
    if alias:
        output = tmp_path / "output-alias"
        output.symlink_to(target, target_is_directory=True)
    module = MVTModule(target_path=str(target), results_path=str(output))

    with pytest.raises(ValueError, match="choose a separate output directory"):
        operation(module)

    assert source.read_text() == '["source evidence"]'
    assert list(target.iterdir()) == [source]


@pytest.mark.parametrize("operation", [run_module, MVTModule.save_to_json])
@pytest.mark.parametrize("input_attribute", ["target_path", "file_path"])
@pytest.mark.parametrize("filename", ["mvt_module.json", "mvt_module_detected.json"])
def test_module_cannot_overwrite_an_input_file(
    tmp_path, operation, input_attribute, filename
):
    source = tmp_path / filename
    source.write_text('["source evidence"]')
    module = MVTModule(results_path=str(tmp_path), **{input_attribute: str(source)})

    with pytest.raises(ValueError, match="choose a separate output directory"):
        operation(module)

    assert source.read_text() == '["source evidence"]'
