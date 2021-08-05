# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

from setuptools import find_packages, setup

__package_name__ = "mvt"
__version__ = "1.0.16"
__description__ = "Mobile Verification Toolkit"

this_directory = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(this_directory, "README.md")
with open(readme_path, encoding="utf-8") as handle:
    long_description = handle.read()

requires = (
    # Base dependencies:
    "click>=8.0.1",
    "rich>=10.6.0",
    "tld>=0.12.6",
    "tqdm>=4.61.2",
    "requests>=2.26.0",
    "simplejson>=3.17.3",
    # iOS dependencies:
    "biplist>=1.0.3",
    "iOSbackup>=0.9.912",
    # Android dependencies:
    "adb-shell>=0.4.0",
    "libusb1>=1.9.3",
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
    name=__package_name__,
    version=__version__,
    description=__description__,
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
