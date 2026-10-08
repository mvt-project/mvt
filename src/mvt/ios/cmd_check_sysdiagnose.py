# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import gzip
import json
import logging
import os
import shutil
import sys
import tarfile
import zlib
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Optional

from mvt.common.command import Command
from mvt.common.indicators import Indicators
from mvt.common.module import MVTModule

from .modules.sysdiagnose import SYSDIAGNOSE_MODULES

log = logging.getLogger(__name__)


class _StreamingGzipFile(gzip.GzipFile):
    """Deliver available bytes before reporting a missing gzip trailer.

    GzipFile.read(n) tries to fill the entire request. At a truncated end it
    can raise EOFError even after decoding bytes for complete tar members.
    read1() returns those bytes first and raises on the following read. The
    tar stream accepts short reads, so it can retain every complete member.
    """

    def read(self, size: Optional[int] = -1) -> bytes:
        return self.read1(-1 if size is None else size)


class _SysdiagnoseTarInfo(tarfile.TarInfo):
    @classmethod
    def fromtarfile(cls, archive: tarfile.TarFile) -> "_SysdiagnoseTarInfo":
        try:
            return super().fromtarfile(archive)
        except (
            tarfile.EmptyHeaderError,  # type: ignore[attr-defined]
            tarfile.TruncatedHeaderError,  # type: ignore[attr-defined]
            tarfile.InvalidHeaderError,  # type: ignore[attr-defined]
        ) as exc:
            # TarFile otherwise treats a short/invalid header after its first
            # member as an ordinary end of archive, hiding the truncation.
            raise tarfile.ReadError(str(exc)) from exc


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
        self.modules = SYSDIAGNOSE_MODULES
        self.sysdiagnose_format: Optional[str] = None
        self.sysdiagnose_archive: Optional[tarfile.TarFile] = None
        self.sysdiagnose_files: list[str] = []
        self.ips_files: list[dict[str, Any]] = []
        self.temp_sysdiagnose_dir: Optional[TemporaryDirectory[str]] = None
        self.extracted_sysdiagnose_path: Optional[str] = None
        self.sysdiagnose_tar_members: list[tarfile.TarInfo] = []
        self.archive_incomplete = False

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

        self.log.info("Checking iOS sysdiagnose at path: %s", self.target_path)

        if os.path.isdir(self.target_path):
            self.sysdiagnose_format = "dir"
            parent_path = Path(self.target_path).absolute().parent
            for root, _, filenames in os.walk(self.target_path):
                for filename in filenames:
                    if filename.startswith("._"):
                        continue
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
        try:
            with _StreamingGzipFile(self.target_path, "rb") as compressed:
                self.sysdiagnose_archive = tarfile.open(
                    fileobj=compressed, mode="r|", tarinfo=_SysdiagnoseTarInfo
                )
                self._extract_sysdiagnose_archive()
                # Tar stops at its end marker, which can precede the gzip
                # trailer. Drain the compressed stream to check its EOF/CRC.
                if not self.archive_incomplete:
                    try:
                        while compressed.read1(1024 * 1024):
                            pass
                    except (EOFError, gzip.BadGzipFile, zlib.error) as exc:
                        self._warn_incomplete_archive(exc)
        except (tarfile.ReadError, EOFError, zlib.error, OSError) as exc:
            self.log.critical(
                "Unable to read the sysdiagnose archive %s: %s. "
                "The file may be truncated or not a gzip-compressed tarball.",
                self.target_path,
                exc,
            )
            self.finish()
            sys.exit(1)

    def _warn_incomplete_archive(self, exc: Exception) -> None:
        self.archive_incomplete = True
        self.log.warning(
            "The sysdiagnose archive is truncated or damaged: %s. Recovered "
            "%d complete files; incomplete files are excluded. Analysis will "
            "be partial and archive integrity cannot be verified. Obtain a "
            "complete copy for a full analysis.",
            exc,
            len(self.sysdiagnose_files),
        )

    def _extract_sysdiagnose_archive(self) -> None:
        archive = self.sysdiagnose_archive
        if archive is None:
            raise RuntimeError("Sysdiagnose archive has not been initialized")

        self.temp_sysdiagnose_dir = TemporaryDirectory()
        extraction_root = Path(self.temp_sysdiagnose_dir.name).resolve()
        archive_roots: set[str] = set()

        try:
            for member in archive:
                self._extract_member(archive, member, extraction_root, archive_roots)
        except (tarfile.ReadError, EOFError, gzip.BadGzipFile, zlib.error) as exc:
            self._warn_incomplete_archive(exc)
            if not self.sysdiagnose_files:
                raise tarfile.ReadError(
                    "No complete sysdiagnose files could be recovered"
                ) from exc

        if len(archive_roots) != 1:
            self.finish()
            raise ValueError("Sysdiagnose archive must contain one top-level directory")

        self.extracted_sysdiagnose_path = str(extraction_root / archive_roots.pop())

    def _extract_member(
        self,
        archive: tarfile.TarFile,
        member: tarfile.TarInfo,
        extraction_root: Path,
        archive_roots: set[str],
    ) -> None:
        member_path = PurePosixPath(member.name.replace("\\", "/"))
        if member_path.is_absolute() or ".." in member_path.parts:
            self.log.warning("Skipping unsafe sysdiagnose path %r", member.name)
            return

        destination = extraction_root.joinpath(*member_path.parts).resolve()
        if not destination.is_relative_to(extraction_root):
            self.log.warning("Skipping unsafe sysdiagnose path %r", member.name)
            return

        if not member_path.parts:
            return
        # AppleDouble sidecars (._name) carry a file's extended attributes,
        # not sysdiagnose content. Device archives hold hundreds of them;
        # bsdtar hides them from listings, tarfile does not.
        if member_path.name.startswith("._"):
            return
        archive_roots.add(member_path.parts[0])

        if member.isdir():
            destination.mkdir(parents=True, exist_ok=True)
            self.sysdiagnose_tar_members.append(member)
            return

        # Modules only need directories and regular files. Do not materialize
        # links or device nodes from an untrusted sysdiagnose archive.
        if not member.isfile():
            self.log.warning("Skipping unsafe sysdiagnose member %r", member.name)
            return

        normalized_name = member_path.as_posix()

        source = archive.extractfile(member)
        if source is None:
            return

        destination.parent.mkdir(parents=True, exist_ok=True)
        # Stage each file independently. A truncated member must never be
        # indexed or left for a module that scans the extracted directory.
        # Staging also preserves an earlier complete entry with the same name.
        with NamedTemporaryFile(dir=destination.parent, delete=False) as output:
            staged_path = Path(output.name)
            try:
                with source:
                    shutil.copyfileobj(source, output)
                if output.tell() != member.size:
                    raise tarfile.ReadError("Unexpected end of sysdiagnose member")
            except BaseException:
                output.close()
                staged_path.unlink(missing_ok=True)
                raise
        try:
            staged_path.replace(destination)
        finally:
            staged_path.unlink(missing_ok=True)
        self.sysdiagnose_files.append(normalized_name)
        self.sysdiagnose_tar_members.append(member)

        if normalized_name.endswith(".ips"):
            self._add_ips_file(str(destination), destination.read_bytes())

    def module_init(self, module) -> None:
        module.ips_files = self.ips_files
        if self.sysdiagnose_format == "tar":
            if self.extracted_sysdiagnose_path is None:
                raise RuntimeError("Sysdiagnose archive has not been extracted")
            module.sysdiagnose_tar_members = self.sysdiagnose_tar_members
            module.sysdiagnose_archive_incomplete = self.archive_incomplete
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
