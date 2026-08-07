# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
import shutil
import tarfile
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any, Optional

from mvt.common.command import Command
from mvt.common.indicators import Indicators
from mvt.common.module import MVTModule

log = logging.getLogger(__name__)


class CmdIOSCheckSysdiagnose(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        iocs: Optional[Indicators] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: bool = False,
        sub_command: bool = False,
        disable_version_check: bool = False,
        disable_indicator_check: bool = False,
        custom_modules: Optional[list[type[MVTModule]]] = None,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            iocs=iocs,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            hashes=hashes,
            sub_command=sub_command,
            log=log,
            disable_version_check=disable_version_check,
            disable_indicator_check=disable_indicator_check,
            custom_modules=custom_modules,
        )
        self.platform = "ios"
        self.name = "check-sysdiagnose"
        self.sysdiagnose_format: Optional[str] = None
        self.sysdiagnose_archive: Optional[tarfile.TarFile] = None
        self.sysdiagnose_files: list[str] = []
        self.ips_files: list[dict[str, Any]] = []
        self.temp_sysdiagnose_dir: Optional[TemporaryDirectory[str]] = None
        self.extracted_sysdiagnose_path: Optional[str] = None

    @staticmethod
    def _parse_bugtype_header(data: bytes) -> Optional[int]:
        try:
            header = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
            return int(header["bug_type"])
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError, ValueError):
            return None

    def _add_ips_file(self, file_path: str, data: bytes) -> None:
        bug_type = self._parse_bugtype_header(data)
        if bug_type is not None:
            self.ips_files.append({"file_path": file_path, "bug_type": bug_type})

    def init(self) -> None:
        if not self.target_path:
            raise ValueError("A sysdiagnose path is required")

        if os.path.isdir(self.target_path):
            self.sysdiagnose_format = "dir"
            parent_path = Path(self.target_path).absolute().parent
            for root, _, filenames in os.walk(self.target_path):
                for filename in filenames:
                    absolute_path = os.path.join(root, filename)
                    file_path = os.path.relpath(absolute_path, parent_path)
                    self.sysdiagnose_files.append(file_path)
                    if filename.endswith(".ips"):
                        with open(absolute_path, "rb") as handle:
                            self._add_ips_file(absolute_path, handle.read())
            return

        if not os.path.isfile(self.target_path):
            raise ValueError(f"Sysdiagnose path does not exist: {self.target_path}")

        self.log.info("Parsing sysdiagnose archive. This might take a while...")
        self.sysdiagnose_format = "tar"
        self.sysdiagnose_archive = tarfile.open(self.target_path, "r:gz")
        self._extract_sysdiagnose_archive()

    def _extract_sysdiagnose_archive(self) -> None:
        archive = self.sysdiagnose_archive
        if archive is None:
            raise RuntimeError("Sysdiagnose archive has not been initialized")

        self.temp_sysdiagnose_dir = TemporaryDirectory()
        extraction_root = Path(self.temp_sysdiagnose_dir.name).resolve()
        archive_roots = set()

        for member in archive:
            member_path = PurePosixPath(member.name.replace("\\", "/"))
            if member_path.is_absolute() or ".." in member_path.parts:
                self.log.warning("Skipping unsafe sysdiagnose path %r", member.name)
                continue

            destination = extraction_root.joinpath(*member_path.parts).resolve()
            if not destination.is_relative_to(extraction_root):
                self.log.warning("Skipping unsafe sysdiagnose path %r", member.name)
                continue

            if not member_path.parts:
                continue
            archive_roots.add(member_path.parts[0])

            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue

            # Modules only need directories and regular files. Do not materialize
            # links or device nodes from an untrusted sysdiagnose archive.
            if not member.isfile():
                self.log.warning("Skipping unsafe sysdiagnose member %r", member.name)
                continue

            normalized_name = member_path.as_posix()
            self.sysdiagnose_files.append(normalized_name)

            source = archive.extractfile(member)
            if source is None:
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            with source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)

            if normalized_name.endswith(".ips"):
                self._add_ips_file(str(destination), destination.read_bytes())

        if len(archive_roots) != 1:
            raise ValueError("Sysdiagnose archive must contain one top-level directory")

        self.extracted_sysdiagnose_path = str(extraction_root / archive_roots.pop())

    def module_init(self, module) -> None:
        module.ips_files = self.ips_files
        if self.sysdiagnose_format == "tar":
            if self.extracted_sysdiagnose_path is None:
                raise RuntimeError("Sysdiagnose archive has not been extracted")
            module.from_sysdiagnose_folder(
                self.extracted_sysdiagnose_path, self.sysdiagnose_files
            )
            return
        if self.sysdiagnose_format == "dir" and self.target_path:
            module.from_sysdiagnose_folder(self.target_path, self.sysdiagnose_files)
            return
        raise RuntimeError("Sysdiagnose input has not been initialized")

    def finish(self) -> None:
        if self.sysdiagnose_archive is not None:
            self.sysdiagnose_archive.close()
            self.sysdiagnose_archive = None
        if self.temp_sysdiagnose_dir is not None:
            self.temp_sysdiagnose_dir.cleanup()
            self.temp_sysdiagnose_dir = None
