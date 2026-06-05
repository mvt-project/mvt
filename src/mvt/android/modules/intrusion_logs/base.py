# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Optional, Union

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[no-redef]

from mvt.common.module import MVTModule
from mvt.common.utils import convert_datetime_to_iso, convert_unix_to_iso


class IntrusionLogsModule(MVTModule):
    """Base class for modules analyzing intrusion logs (newline-delimited JSON).

    Performance note
    ----------------
    Log files can be large and are shared by every module in this package.
    To avoid re-reading and re-parsing the same files N times (once per
    module), the command layer should call :meth:`load_all_events` exactly
    once and then assign the returned dict to the ``il_events_by_type``
    attribute of every module instance **before** calling ``run_module``.

    When ``il_events_by_type`` is populated:
    * :meth:`collect_txt` becomes a no-op (no disk I/O).
    * :meth:`parse_collected_txt` iterates the in-memory list for the
      requested event type instead of re-parsing raw text.

    Modules that are used standalone (e.g. in tests) still work as before
    because ``il_events_by_type`` defaults to ``None``, which preserves the
    original file-loading code path.
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )
        # Raw file content collected by collect_txt (fallback path only).
        self.il_files: list[tuple[str, str]] = []

        # Pre-parsed events injected by the command layer.
        # Keys are event-type strings (e.g. "dns_event"), values are lists of
        # raw event-data dicts exactly as they appear in the JSON lines.
        # When this is not None, collect_txt and parse_collected_txt use it
        # instead of touching the file system.
        self.il_events_by_type: Optional[dict[str, list[dict]]] = None

    # ------------------------------------------------------------------
    # Serialization helper
    # ------------------------------------------------------------------

    def serialize(self, record: dict) -> Union[dict, list]:
        """Serialize a record for timeline output."""
        return {
            "timestamp": record.get("timestamp", record.get("isodate")),
            "module": self.__class__.__name__,
            "event": record.get("event_type", ""),
            "data": str(record),
        }

    # ------------------------------------------------------------------
    # File collection
    # ------------------------------------------------------------------

    def collect_txt(self, source) -> None:
        """Collect text log files from *source* into ``self.il_files``.

        Entry points:
        * directory → walk recursively
        * zip file  → walk zip entries
        * anything else → silently skip

        If ``self.il_events_by_type`` has already been populated (i.e. the
        command layer pre-loaded the events), this method returns immediately
        without any disk I/O.
        """
        if self.il_events_by_type is not None:
            self.log.debug(
                "Pre-loaded events available — skipping file collection for %s",
                self.__class__.__name__,
            )
            return

        path = Path(source)

        if path.is_dir():
            self._walk_directory(path)
            return

        if path.is_file() and path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path) as z:
                    self._walk_zip(z)
            except zipfile.BadZipFile:
                self.log.debug("Skipping invalid zip: %s", path)
            return

        self.log.debug("Skipping unsupported source: %s", source)

    def _walk_directory(self, root: Path, prefix: str = "") -> None:
        for item in root.iterdir():
            if item.is_dir():
                self._walk_directory(item, prefix=f"{prefix}{item.name}/")
                continue

            if item.suffix.lower() == ".txt":
                self.il_files.append(
                    (f"{prefix}{item.name}", item.read_text(errors="ignore"))
                )

            elif item.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(item) as z:
                        self._walk_zip(z, prefix=f"{prefix}{item.name}::")
                except zipfile.BadZipFile:
                    self.log.warning("Skipping invalid zip: %s", item)

    def _walk_zip(self, zf: zipfile.ZipFile, prefix: str = "") -> None:
        for info in zf.infolist():
            if info.is_dir():
                continue

            name = info.filename
            with zf.open(info) as f:
                data = f.read()

            if name.lower().endswith(".txt"):
                self.il_files.append((f"{prefix}{name}", data.decode(errors="ignore")))

            elif name.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as inner:
                    self._walk_zip(inner, prefix=f"{prefix}{name}::")

    # ------------------------------------------------------------------
    # Single-pass loader (used by the command layer)
    # ------------------------------------------------------------------

    def load_all_events(self, source) -> dict[str, list[dict]]:
        """Read every log file under *source* **once** and parse all JSON
        lines in a single pass, routing events into per-type buckets.

        Returns a ``dict`` mapping *event_type* strings to lists of raw
        event-data dicts.  The result is also stored in
        ``self.il_events_by_type`` so that subsequent calls to
        :meth:`collect_txt` and :meth:`parse_collected_txt` on *this*
        instance are no-ops.

        Intended usage in the command layer::

            loader = IntrusionLogsModule(target_path=target, log=log)
            all_events = loader.load_all_events(target)

            for module_cls in INTRUSION_LOGS_MODULES:
                m = module_cls(target_path=target, ...)
                m.il_events_by_type = all_events   # inject — no re-reading
                run_module(m)
        """
        # Reset so that _collect_txt actually runs (il_events_by_type is None).
        self.il_events_by_type = None
        self.il_files = []
        self.collect_txt(source)

        events_by_type: dict[str, list[dict]] = {}
        # JSON fingerprints used to drop events that appear in more than one
        # log file (overlapping daily files are the most common source of
        # cross-file duplicates).
        seen_fingerprints: set[str] = set()
        total_lines = 0
        skipped_lines = 0
        duplicate_lines = 0

        for file_name, text in self.il_files:
            for line_num, line in enumerate(text.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue

                total_lines += 1
                try:
                    entry = json.loads(line)
                    for event_type, event_data in entry.items():
                        if isinstance(event_data, dict):
                            fingerprint = json.dumps(event_data, sort_keys=True)
                            if fingerprint in seen_fingerprints:
                                duplicate_lines += 1
                                continue
                            seen_fingerprints.add(fingerprint)
                            events_by_type.setdefault(event_type, []).append(event_data)
                except json.JSONDecodeError as e:
                    skipped_lines += 1
                    self.log.warning(
                        "Failed to parse JSON on line %d in %s: %s",
                        line_num,
                        file_name,
                        e,
                    )
                except Exception as e:
                    skipped_lines += 1
                    self.log.warning(
                        "Error processing line %d in %s: %s",
                        line_num,
                        file_name,
                        e,
                    )

        if duplicate_lines:
            self.log.info(
                "Removed %d duplicate event(s) seen across multiple log files",
                duplicate_lines,
            )

        self.log.info(
            "Loaded %d log files, parsed %d lines (%d skipped), found event types: %s",
            len(self.il_files),
            total_lines,
            skipped_lines,
            {k: len(v) for k, v in events_by_type.items()},
        )

        # Cache so this instance also benefits from the fast path.
        self.il_events_by_type = events_by_type
        return events_by_type

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_collected_txt(self, event_type: str) -> None:
        """Parse collected log text and dispatch events of *event_type*.

        Fast path
        ~~~~~~~~~
        When ``self.il_events_by_type`` is populated (injected by the command
        layer after a single shared :meth:`load_all_events` call), the method
        iterates the already-parsed in-memory list for *event_type* — no
        re-reading, no re-parsing of JSON.

        Fallback path
        ~~~~~~~~~~~~~
        When ``self.il_events_by_type`` is ``None``, the method falls back to
        iterating ``self.il_files`` and parsing each JSON line, which is the
        original behaviour.
        """
        if self.il_events_by_type is not None:
            events = self.il_events_by_type.get(event_type, [])
            self.log.debug(
                "Using pre-loaded events: dispatching %d '%s' events",
                len(events),
                event_type,
            )
            for event_data in events:
                try:
                    # Work on a shallow copy so that mutations in one module
                    # (e.g. adding "timestamp") do not affect other modules
                    # that share the same dict reference.
                    self.process_event(dict(event_data))
                except Exception as e:
                    self.log.warning(
                        "Error processing pre-parsed '%s' event: %s",
                        event_type,
                        e,
                    )
            return

        # Fallback: parse raw text collected by collect_txt().
        # Use the same JSON-fingerprint approach as MVTModule._deduplicate_timeline
        # to drop events that appear verbatim in more than one log file.
        seen_fingerprints: set[str] = set()
        duplicate_count = 0
        for file_name, text in self.il_files:
            for line_num, line in enumerate(text.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if event_type in entry:
                        event_data = entry[event_type]
                        fingerprint = json.dumps(event_data, sort_keys=True)
                        if fingerprint in seen_fingerprints:
                            duplicate_count += 1
                            continue
                        seen_fingerprints.add(fingerprint)
                        event_data["event_type"] = event_type
                        self.process_event(event_data)
                except json.JSONDecodeError as e:
                    self.log.warning(
                        "Failed to parse JSON on line %d in %s: %s",
                        line_num,
                        file_name,
                        str(e),
                    )
                except Exception as e:
                    self.log.warning(
                        "Error processing line %d in %s: %s",
                        line_num,
                        file_name,
                        str(e),
                    )
        if duplicate_count:
            self.log.info(
                "Removed %d duplicate '%s' event(s) seen across multiple log files",
                duplicate_count,
                event_type,
            )

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    def process_event(self, event_data: dict) -> None:
        """Process an individual event.  Override this in subclasses.

        Args:
            event_data: Dictionary containing the event data.
        """
        self.results.append(event_data)

    # ------------------------------------------------------------------
    # Timestamp localisation
    # ------------------------------------------------------------------

    def _localize_timestamp(self, event_time_seconds: float) -> str:
        """Convert a Unix timestamp (in seconds) to an ISO string.

        When the device timezone is available via ``module_options["device_timezone"]``
        (a IANA timezone name such as ``"Europe/Paris"`` read from
        ``persist.sys.timezone`` in ``getprop.txt``), the UTC instant is
        converted to the device's local time before formatting — mirroring the
        approach used by ``AQFFiles``.

        When no timezone is configured the method falls back to UTC, which is
        consistent with all other MVT modules that call ``convert_unix_to_iso``.

        Args:
            event_time_seconds: Unix epoch timestamp expressed in **seconds**
                (callers are responsible for dividing ms/ns values first).

        Returns:
            ISO-formatted datetime string (``YYYY-mm-dd HH:MM:SS.ffffff``).
            The string always represents the device-local time (or UTC when no
            timezone is known); no UTC offset suffix is appended, matching the
            format produced by :func:`mvt.common.utils.convert_unix_to_iso`.
        """
        tz_name: Optional[str] = self.module_options.get("device_timezone")
        if tz_name:
            try:
                device_tz = zoneinfo.ZoneInfo(tz_name)
                utc_dt = datetime.datetime.fromtimestamp(
                    event_time_seconds, tz=datetime.timezone.utc
                )
                local_dt = utc_dt.astimezone(device_tz)
                # Strip tzinfo so that convert_datetime_to_iso outputs the
                # local wall-clock time without a timezone suffix.  This is
                # the same pattern used by AQFFiles.
                return convert_datetime_to_iso(local_dt.replace(tzinfo=None))
            except Exception as e:
                self.log.warning(
                    "Could not apply device timezone '%s', falling back to UTC: %s",
                    tz_name,
                    e,
                )

        return convert_unix_to_iso(event_time_seconds)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Main execution method.  Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the run() method")
