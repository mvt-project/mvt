# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

from setuptools import find_packages, setup

from mvt.common.version import MVT_VERSION

this_directory = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(this_directory, "README.md")
with open(readme_path, encoding="utf-8") as handle:
    long_description = handle.read()

requires = (
    # Base dependencies:
    "click>=8.0.3",
    "rich>=10.12.0",
    "tld>=0.12.6",
    "tqdm>=4.62.3",
    "requests>=2.26.0",
    "simplejson>=3.17.5",
    "packaging>=21.0",
    "appdirs>=1.4.4",
    # iOS dependencies:
    "iOSbackup>=0.9.921",
    # Android dependencies:
    "adb-shell>=0.4.2",
    "libusb1>=2.0.1",
    "cryptography>=36.0.1"
)


def get_package_data(package):
    walk = [(dirpath.replace(package + os.sep, "", 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)
            if not os.path.exists(os.path.join(dirpath, "__init__.py"))]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename)
                          for filename in filenames])
    return {package: filepaths}


setup(
    name="mvt",
    version=MVT_VERSION,
    description="Mobile Verification Toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mvt-project/mvt",
    entry_points={
        "console_scripts": [
            "mvt-ios = mvt.ios:cli",
            "mvt-android = mvt.android:cli",
        ],
    },
    install_requires=requires,
    packages=find_packages(),
    package_data=get_package_data("mvt"),
    include_package_data=True,
    keywords="security mobile forensics malware",
    license="MVT",
    classifiers=[
    ],
)
