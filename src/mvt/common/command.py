# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
import queue
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from heapq import heappop, heappush
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .alerts import AlertLevel, AlertStore
from .config import settings
from .indicators import Indicators
from .log import MVTLogHandler, finish_module_log_buffer, start_module_log_buffer
from .module import EncryptedBackupError, MVTModule, run_module, save_timeline
from .module_loader import module_supports_command
from .module_types import ModuleTimeline
from .utils import (
    CustomJSONEncoder,
    convert_datetime_to_iso,
    generate_hashes_from_path,
    get_sha256_from_file_path,
)
from .version import MVT_VERSION


class Command:
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        iocs: Optional[Indicators] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: Optional[bool] = False,
        sub_command: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        disable_version_check: bool = False,
        disable_indicator_check: bool = False,
        custom_modules: Optional[list[type[MVTModule]]] = None,
        jobs: int = 4,
    ) -> None:
        self.name = ""
        self.platform = ""
        self.modules: list[type[MVTModule]] = []
        self.custom_modules = custom_modules if custom_modules else []

        self.target_path = target_path
        self.results_path = results_path
        self.ioc_files = ioc_files if ioc_files else []
        self.module_name = module_name
        self.serial = serial
        self.log = log
        self.sub_command = sub_command
        self.disable_version_check = disable_version_check
        self.disable_indicator_check = disable_indicator_check
        if jobs < 1:
            raise ValueError("jobs must be at least 1")
        self.jobs = jobs
        self._resource_lock = threading.RLock()
        self._resource_cache: dict[object, Any] = {}

        # This dictionary can contain options that will be passed down from
        # the Command to all modules. This can for example be used to pass
        # down a password to decrypt a backup or flags which are need by some modules.
        self.module_options = module_options if module_options else {}

        # This list will contain all executed modules.
        # We can use this to reference e.g. self.executed[0].results.
        self.executed: list[MVTModule] = []
        self.hashes = hashes
        self.hash_values: list[dict[str, Any]] = []
        self.timeline: ModuleTimeline = []

        # Load IOCs
        self._create_storage()
        self._setup_logging()

        if iocs is not None:
            self.iocs = iocs
        else:
            self.iocs = Indicators(self.log)
            self.iocs.load_indicators_files(self.ioc_files)

        self.alertstore = AlertStore()

    def _create_storage(self) -> None:
        if self.results_path and not os.path.exists(self.results_path):
            try:
                os.makedirs(self.results_path)
            except Exception as exc:
                self.log.fatal(
                    "Unable to create output folder %s: %s", self.results_path, exc
                )
                sys.exit(1)

    def _setup_logging(self):
        if not self.results_path:
            return

        logger = logging.getLogger("mvt")
        file_handler = logging.FileHandler(
            os.path.join(self.results_path, "command.log")
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # MVT can be run in a loop.
        # Old file handlers stick around in subsequent loops.
        # Remove any existing logging.FileHandler instances.
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)

        # And finally add the new one.
        logger.addHandler(file_handler)

    def _store_timeline(self) -> None:
        if not self.results_path:
            return

        # We use local timestamps in the timeline on Android as many
        # logs do not contain timezone information.
        if type(self).__name__.startswith("CmdAndroid"):
            is_utc = False
        else:
            is_utc = True

        if len(self.timeline) > 0:
            save_timeline(
                self.timeline,
                os.path.join(self.results_path, "timeline.csv"),
                is_utc=is_utc,
            )

    def _store_alerts(self) -> None:
        if not self.results_path:
            return

        alerts = self.alertstore.as_json()
        if not alerts:
            return

        alerts_path = os.path.join(self.results_path, "alerts.json")
        with open(alerts_path, "w+", encoding="utf-8") as handle:
            json.dump(alerts, handle, indent=4, cls=CustomJSONEncoder)

    def _store_alerts_timeline(self) -> None:
        if not self.results_path:
            return

        alerts_timeline_path = os.path.join(self.results_path, "alerts_timeline.csv")
        self.alertstore.save_timeline(alerts_timeline_path)

    def _store_info(self) -> None:
        if not self.results_path:
            return

        target_path: Optional[str] = None
        if self.target_path:
            target_path = os.path.abspath(self.target_path)

        info: dict[str, Any] = {
            "target_path": target_path,
            "mvt_version": MVT_VERSION,
            "date": convert_datetime_to_iso(datetime.now()),
            "ioc_files": [],
            "hashes": [],
        }

        for coll in self.iocs.ioc_collections:
            ioc_file_path = coll.get("stix2_file_path", "")
            if ioc_file_path and ioc_file_path not in info["ioc_files"]:
                info["ioc_files"].append(ioc_file_path)

        if self.target_path and (settings.HASH_FILES or self.hashes):
            self.generate_hashes()

        info["hashes"] = self.hash_values

        info_path = os.path.join(self.results_path, "info.json")
        with open(info_path, "w+", encoding="utf-8") as handle:
            json.dump(info, handle, indent=4)

        if self.target_path and (settings.HASH_FILES or self.hashes):
            info_hash = get_sha256_from_file_path(info_path)
            self.log.info('Reference hash of the info.json file: "%s"', info_hash)

    def generate_hashes(self) -> None:
        """
        Compute hashes for files in the target_path
        """
        if not self.target_path:
            return

        for file in generate_hashes_from_path(self.target_path, self.log):
            self.hash_values.append(file)

    def list_modules(self) -> None:
        self.log.info("Following is the list of available %s modules:", self.name)
        for module in self._available_modules():
            self.log.info(" - %s", module.__name__)

    def _available_modules(self) -> list[type[MVTModule]]:
        modules = list(self.modules)
        modules.extend(
            module
            for module in self.custom_modules
            if module_supports_command(module, self.platform, self.name)
        )

        deduplicated = []
        for module in modules:
            if module not in deduplicated:
                deduplicated.append(module)

        return deduplicated

    def init(self) -> None:
        raise NotImplementedError

    def module_init(self, module: MVTModule) -> None:
        raise NotImplementedError

    def finish(self) -> None:
        raise NotImplementedError

    def show_alerts_brief(self) -> None:
        console = Console()

        message = Text()
        for i, level in enumerate(AlertLevel):
            message.append(
                f"MVT produced {self.alertstore.count(level)} {level.name} alerts."
            )
            if i < len(AlertLevel) - 1:
                message.append("\n")

        panel = Panel(
            message, title="ALERTS", style="sandy_brown", border_style="sandy_brown"
        )
        console.print("")
        console.print(panel)

    def show_disable_adb_warning(self) -> None:
        console = Console()
        message = Text(
            "Please disable Developer Options and ADB (Android Debug Bridge) on the device once finished with the acquisition. "
            "ADB is a powerful tool which can allow unauthorized access to the device."
        )
        panel = Panel(message, title="NOTE", style="yellow", border_style="yellow")
        console.print("")
        console.print(panel)

    def show_support_message(self) -> None:
        console = Console()
        message = Text()

        support_message = "Please seek reputable expert help if you have serious concerns about a possible spyware attack. Such support is available to human rights defenders and civil society through Amnesty International's Security Lab at https://securitylab.amnesty.org/get-help/?c=mvt"
        if (
            self.alertstore.count(AlertLevel.HIGH) > 0
            or self.alertstore.count(AlertLevel.CRITICAL) > 0
        ):
            message.append(
                f"MVT produced HIGH or CRITICAL alerts. Only expert review can confirm if the detected indicators are signs of an attack.\n\n{support_message}",
            )
            panel = Panel(message, title="WARNING", style="red", border_style="red")
        else:
            message.append(
                f"The lack of severe alerts does not equate to a clean bill of health.\n\n{support_message}",
            )
            panel = Panel(message, title="NOTE", style="yellow", border_style="yellow")

        console.print("")
        console.print(panel)

    def _ordered_modules(self) -> Optional[list[type[MVTModule]]]:
        """Return enabled modules in stable topological order."""
        modules = self._available_modules()
        module_indexes = {module: index for index, module in enumerate(modules)}

        if self.module_name:
            selected = [
                module for module in modules if module.__name__ == self.module_name
            ]
        else:
            selected = [module for module in modules if module.enabled]

        required = set(selected)
        pending = list(selected)
        while pending:
            module = pending.pop()
            for dependency in module.dependencies:
                if dependency not in module_indexes:
                    self.log.warning(
                        "Module %s depends on unavailable module %s. "
                        "No modules will be run.",
                        module.__name__,
                        dependency.__name__,
                    )
                    return None
                if dependency not in required:
                    required.add(dependency)
                    pending.append(dependency)

        dependents: dict[type[MVTModule], list[type[MVTModule]]] = {
            module: [] for module in required
        }
        indegree = {module: 0 for module in required}
        for module in required:
            for dependency in module.dependencies:
                if dependency not in required:
                    continue
                dependents[dependency].append(module)
                indegree[module] += 1

        ready: list[tuple[int, type[MVTModule]]] = []
        for module, count in indegree.items():
            if count == 0:
                heappush(ready, (module_indexes[module], module))

        ordered = []
        while ready:
            _, module = heappop(ready)
            ordered.append(module)
            for dependent in dependents[module]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    heappush(ready, (module_indexes[dependent], dependent))

        if len(ordered) != len(required):
            cyclic_modules = sorted(
                (module.__name__ for module, count in indegree.items() if count > 0)
            )
            self.log.warning(
                "Circular module dependency detected involving: %s. "
                "No modules will be run.",
                ", ".join(cyclic_modules),
            )
            return None

        return ordered

    def _run_module(
        self,
        module: type[MVTModule],
        executed_by_type: dict[type[MVTModule], MVTModule],
        capture_logs: bool,
    ) -> tuple[MVTModule, list[logging.LogRecord], bool]:
        """Initialize and run one module, optionally buffering console logs."""
        token = start_module_log_buffer() if capture_logs else None
        records: list[logging.LogRecord] = []
        encrypted = False
        try:
            m = module(
                target_path=self.target_path,
                results_path=self.results_path,
                module_options=self.module_options,
                log=logging.getLogger(module.__module__),
            )
            m.dependency_modules = {
                dependency: executed_by_type[dependency]
                for dependency in module.dependencies
            }
            m.resource_lock = self._resource_lock
            m.resource_cache = self._resource_cache

            if self.iocs.total_ioc_count:
                # IOC collections are shared read-only during module execution.
                m.indicators = self.iocs

            if self.serial:
                m.serial = self.serial

            try:
                self.module_init(m)
            except NotImplementedError:
                pass

            try:
                run_module(m)
            except EncryptedBackupError:
                encrypted = True
        finally:
            if token is not None:
                records = finish_module_log_buffer(token)

        return m, records, encrypted

    @staticmethod
    def _console_handler() -> Optional[MVTLogHandler]:
        for handler in reversed(logging.getLogger("mvt").handlers):
            if isinstance(handler, MVTLogHandler):
                return handler
        return None

    def _aggregate_modules(
        self,
        ordered_modules: list[type[MVTModule]],
        completed: dict[type[MVTModule], MVTModule],
    ) -> None:
        """Aggregate results in stable topological order."""
        for module in ordered_modules:
            if module not in completed:
                continue
            instance = completed[module]
            self.executed.append(instance)
            self.timeline.extend(instance.timeline)
            self.alertstore.extend(instance.alertstore.alerts)

    def _run_sequential(
        self, ordered_modules: list[type[MVTModule]]
    ) -> tuple[dict[type[MVTModule], MVTModule], bool]:
        completed: dict[type[MVTModule], MVTModule] = {}
        for module in ordered_modules:
            instance, _, encrypted = self._run_module(module, completed, False)
            if encrypted:
                return completed, True
            completed[module] = instance
        return completed, False

    def _run_parallel(
        self, ordered_modules: list[type[MVTModule]], jobs: int
    ) -> tuple[dict[type[MVTModule], MVTModule], bool]:
        """Run a stable module DAG with bounded worker threads."""
        completed: dict[type[MVTModule], MVTModule] = {}
        scheduled: set[type[MVTModule]] = set()
        running: dict[Future, type[MVTModule]] = {}
        completion_queue: queue.Queue[Future] = queue.Queue()
        handler = self._console_handler()
        status = None
        fatal = False

        def ready_modules() -> list[type[MVTModule]]:
            return [
                module
                for module in ordered_modules
                if module not in scheduled
                and all(dependency in completed for dependency in module.dependencies)
            ]

        def update_status() -> None:
            if status is None:
                return
            names = ", ".join(module.__name__ for module in running.values())
            status.update(
                f"Modules: {len(completed)}/{len(ordered_modules)} complete"
                + (f"; running {names}" if names else "")
            )

        if handler and handler.console.is_terminal:
            status = handler.console.status("")
            status.start()

        try:
            with ThreadPoolExecutor(max_workers=jobs) as executor:
                while len(completed) < len(ordered_modules):
                    ready = ready_modules()

                    # An unsafe module is a scheduler barrier: it starts only
                    # after active workers drain and blocks later ready work.
                    if ready and not ready[0].parallel_safe:
                        if running:
                            future = completion_queue.get()
                            module = running.pop(future)
                            instance, records, encrypted = future.result()
                            if handler:
                                handler.emit_module_records(module.__name__, records)
                            if encrypted:
                                fatal = True
                                break
                            completed[module] = instance
                            update_status()
                            continue

                        module = ready[0]
                        scheduled.add(module)
                        if status is not None:
                            status.update(
                                f"Modules: {len(completed)}/{len(ordered_modules)} "
                                f"complete; running {module.__name__}"
                            )
                        instance, records, encrypted = self._run_module(
                            module, completed, True
                        )
                        if handler:
                            handler.emit_module_records(module.__name__, records)
                        if encrypted:
                            fatal = True
                            break
                        completed[module] = instance
                        update_status()
                        continue

                    for module in ready:
                        if len(running) >= jobs or not module.parallel_safe:
                            break
                        scheduled.add(module)
                        future = executor.submit(
                            self._run_module, module, dict(completed), True
                        )
                        running[future] = module
                        future.add_done_callback(completion_queue.put)

                    update_status()
                    if not running:
                        break

                    future = completion_queue.get()
                    module = running.pop(future)
                    instance, records, encrypted = future.result()
                    if handler:
                        handler.emit_module_records(module.__name__, records)
                    if encrypted:
                        fatal = True
                        break
                    completed[module] = instance
                    update_status()

                if fatal:
                    for future in running:
                        future.cancel()
                    # The executor context waits for already-active work. Its
                    # results are intentionally discarded after the fatal error.
        finally:
            if status is not None:
                status.stop()

        return completed, fatal

    def run(self) -> None:
        ordered_modules = self._ordered_modules()
        if ordered_modules is None:
            return

        try:
            self.init()
        except NotImplementedError:
            pass

        jobs = self.jobs
        if settings.PROFILE and jobs > 1:
            self.log.warning(
                "MVT_PROFILE is enabled; forcing sequential module execution."
            )
            jobs = 1

        if jobs == 1:
            completed, fatal = self._run_sequential(ordered_modules)
        else:
            completed, fatal = self._run_parallel(ordered_modules, jobs)

        self._aggregate_modules(ordered_modules, completed)

        try:
            self.finish()
        except NotImplementedError:
            pass

        if fatal:
            self.log.critical(
                "The backup appears to be encrypted. "
                "Please decrypt it first using `mvt-ios decrypt-backup`."
            )
            return

        # We only store the timeline from the parent/main command
        if self.sub_command:
            return

        self._store_timeline()
        self._store_alerts_timeline()
        self._store_alerts()
        self._store_info()
