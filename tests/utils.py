# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
from pathlib import Path


def get_artifact(fname):
    """
    Return the artifact path in the artifact folder
    """
    fpath = os.path.join(get_artifact_folder(), fname)
    if os.path.isfile(fpath):
        return fpath
    return


def get_artifact_folder():
    return os.path.join(os.path.dirname(__file__), "artifacts")


def get_ios_backup_folder():
    return os.path.join(os.path.dirname(__file__), "artifacts", "ios_backup")


def get_android_backup_folder():
    return os.path.join(os.path.dirname(__file__), "artifacts", "android_backup")


def get_android_androidqf():
    return os.path.join(os.path.dirname(__file__), "artifacts", "androidqf")


def get_indicator_file():
    print("PYTEST env", os.getenv("PYTEST_CURRENT_TEST"))


def list_files(path: str):
    files = []
    parent_path = Path(path).absolute().parent.as_posix()
    target_abs_path = os.path.abspath(path)
    for root, subdirs, subfiles in os.walk(target_abs_path):
        for fname in subfiles:
            file_path = os.path.relpath(os.path.join(root, fname), parent_path)
            files.append(file_path)

    return files
