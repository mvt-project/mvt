# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os


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


def get_indicator_file():
    print("PYTEST env", os.getenv("PYTEST_CURRENT_TEST"))
