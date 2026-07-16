# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Parse AndroidQF protobuf inventory artifacts into MVT result dictionaries."""

from __future__ import annotations

import io
from typing import Any, TypeVar

import betterproto2

from mvt.android.parsers.proto import (
    FilesRecord,
    PackageCertificateRecord,
    PackageFileRecord,
    PackagesRecord,
    StringRecord,
)

T = TypeVar("T", bound=betterproto2.Message)


def _parse_delimited_messages(data: bytes, message_type: type[T]) -> list[T]:
    stream = io.BytesIO(data)
    messages: list[T] = []
    while True:
        if not stream.read(1):
            break
        stream.seek(stream.tell() - 1)
        messages.append(message_type().load(stream, size=betterproto2.SIZE_DELIMITED))
    return messages


def parse_string_records(data: bytes) -> list[str]:
    """Parse root_binaries.pb or mounts.pb into a list of string values."""
    return [record.value for record in _parse_delimited_messages(data, StringRecord)]


def files_record_to_dict(record: FilesRecord) -> dict[str, Any]:
    """Map protobuf file metadata to the AndroidQF files.json result shape."""
    modified_time = int(record.mtime) if record.mtime else 0
    return {
        "path": record.path,
        "size": record.size,
        "mode": record.mode or "",
        "user_id": 0,
        "user_name": record.user or "",
        "group_id": 0,
        "group_name": record.group or "",
        "changed_time": modified_time,
        "modified_time": modified_time,
        "access_time": modified_time,
        "error": "",
        "context": "",
        "sha1": "",
        "sha256": "",
        "sha512": "",
        "md5": "",
    }


def parse_files_records(data: bytes) -> list[dict[str, Any]]:
    """Parse files.pb into MVT file result dictionaries."""
    return [
        files_record_to_dict(record)
        for record in _parse_delimited_messages(data, FilesRecord)
    ]


def _certificate_to_androidqf_dict(
    certificate: PackageCertificateRecord,
) -> dict[str, Any]:
    cert: dict[str, Any] = {}
    if certificate.md5:
        cert["Md5"] = certificate.md5
    if certificate.sha1:
        cert["Sha1"] = certificate.sha1
    if certificate.sha256:
        cert["Sha256"] = certificate.sha256
    if certificate.valid_from:
        cert["ValidFrom"] = certificate.valid_from
    if certificate.valid_to:
        cert["ValidTo"] = certificate.valid_to
    if certificate.issuer:
        cert["Issuer"] = certificate.issuer
    if certificate.subject:
        cert["Subject"] = certificate.subject
    if certificate.signature_algorithm:
        cert["SignatureAlgorithm"] = certificate.signature_algorithm
    if certificate.serial_number:
        try:
            cert["SerialNumber"] = int(certificate.serial_number)
        except ValueError:
            cert["SerialNumber"] = certificate.serial_number
    return cert


def package_file_record_to_dict(file_record: PackageFileRecord) -> dict[str, Any]:
    """Map protobuf package file metadata to the AndroidQF packages.json file shape."""
    result: dict[str, Any] = {
        "path": file_record.path,
        "local_name": file_record.local_name or "",
        "md5": file_record.md5 or "",
        "sha1": file_record.sha1 or "",
        "sha256": file_record.sha256 or "",
        "sha512": file_record.sha512 or "",
        "error": "",
        "verified_certificate": False,
        "certificate_error": "",
        "trusted_certificate": False,
    }
    if file_record.certificates:
        result["certificate"] = _certificate_to_androidqf_dict(
            file_record.certificates[0]
        )
    return result


def packages_record_to_dict(record: PackagesRecord) -> dict[str, Any]:
    """Map protobuf package metadata to the AndroidQF packages.json result shape."""
    return {
        "name": record.name,
        "installer": record.installer or "null",
        "uid": record.uid,
        "disabled": record.disabled,
        "system": record.system,
        "third_party": record.third_party,
        "files": [package_file_record_to_dict(file) for file in record.files],
    }


def parse_packages_records(data: bytes) -> list[dict[str, Any]]:
    """Parse packages.pb into MVT package result dictionaries."""
    return [
        packages_record_to_dict(record)
        for record in _parse_delimited_messages(data, PackagesRecord)
    ]
