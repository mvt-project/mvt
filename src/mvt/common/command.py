# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
import sys
from datetime import datetime
from heapq import heappop, heappush
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .alerts import AlertLevel, AlertStore
from .config import settings
from .indicators import Indicators
from .module import EncryptedBackupError, MVTModule, run_module, save_timeline
from .module_loader import (
    ModuleOrigin,
    get_module_logger,
    get_module_origin,
    module_supports_command,
)
from .module_types import ModuleTimeline, URLResult
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

        # This dictionary can contain options that will be passed down from
        # the Command to all modules. This can for example be used to pass
        # down a password to decrypt a backup or flags which are need by some modules.
        self.module_options = module_options if module_options else {}

        # This dictionary maps the modules which were replaced by a module
        # declaring `replaces` to the module which took their place.
        self.module_replacements: dict[type[MVTModule], type[MVTModule]] = {}

        # This list will contain all executed modules.
        # We can use this to reference e.g. self.executed[0].results.
        self.executed: list[MVTModule] = []
        self.hashes = hashes
        self.hash_values: list[dict[str, Any]] = []
        self.timeline: ModuleTimeline = []
        self.url_results: list[URLResult] = []

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

    def _store_urls(self) -> None:
        if not self.results_path or not self.url_results:
            return

        urls_path = os.path.join(self.results_path, "urls.json")
        with open(urls_path, "w", encoding="utf-8") as handle:
            json.dump(self.url_results, handle, indent=4, cls=CustomJSONEncoder)

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

    @staticmethod
    def _modules_by_origin(
        modules: list[type[MVTModule]],
    ) -> dict[ModuleOrigin, list[str]]:
        origins: dict[ModuleOrigin, list[str]] = {}
        for module in modules:
            origins.setdefault(get_module_origin(module), []).append(module.__name__)
        return origins

    def list_modules(self) -> None:
        self.log.info("Following is the list of available %s modules:", self.name)
        for origin, module_names in self._modules_by_origin(
            self._available_modules()
        ).items():
            self.log.info(
                " - Modules from %s: %s", origin.label, ", ".join(module_names)
            )

    def _log_loaded_modules(self, modules: list[type[MVTModule]]) -> None:
        """Record the loaded modules and their origins for auditability."""
        for origin, module_names in self._modules_by_origin(modules).items():
            self.log.info(
                "Loaded %d %s modules from %s: %s",
                len(module_names),
                self.name,
                origin.label,
                ", ".join(module_names),
            )

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

        available = self._apply_replacements(deduplicated)
        self._warn_about_slug_collisions(available)

        return available

    def _warn_about_slug_collisions(self, modules: list[type[MVTModule]]) -> None:
        """Report modules writing their results to the same file.

        Results are stored in a file named after the module slug, so two
        modules sharing one silently overwrite each other. Replacements are
        already resolved here, so a module deliberately taking over the slug
        of the module it replaces is not reported: the module it replaced is
        no longer part of the run.
        """
        modules_by_slug: dict[str, type[MVTModule]] = {}
        for module in modules:
            slug = module.get_slug()
            first = modules_by_slug.setdefault(slug, module)
            if first is module:
                continue

            self.log.warning(
                "Modules %s from %s and %s from %s both use the slug %s. If "
                "both run, whichever runs last overwrites the results of the "
                "other in %s.json.",
                first.__name__,
                get_module_origin(first).label,
                module.__name__,
                get_module_origin(module).label,
                slug,
                slug,
            )

    def _declared_replacements(
        self, modules: list[type[MVTModule]]
    ) -> dict[type[MVTModule], type[MVTModule]]:
        """Return the replacements declared by the given modules."""
        replacements: dict[type[MVTModule], type[MVTModule]] = {}
        for module in modules:
            replaced = module.replaces
            if replaced is None or replaced is module:
                continue

            if not module.enabled:
                # Replacing a module must not disable it, as a disabled
                # replacement never runs in its place.
                self.log.debug(
                    "Module %s is disabled and does not replace module %s.",
                    module.__name__,
                    replaced.__name__,
                )
                continue

            if replaced not in modules:
                # A module can support several commands while the module it
                # replaces is only available in some of them.
                self.log.debug(
                    "Module %s replaces module %s, which is not available "
                    "for the %s command.",
                    module.__name__,
                    replaced.__name__,
                    self.name,
                )
                continue

            if replaced in replacements:
                self.log.warning(
                    "Modules %s and %s both replace module %s. Both of them "
                    "will run, %s will not, and modules depending on %s will "
                    "use the results of %s. Replacements which share the slug "
                    "of %s overwrite each other's results file.",
                    replacements[replaced].__name__,
                    module.__name__,
                    replaced.__name__,
                    replaced.__name__,
                    replaced.__name__,
                    replacements[replaced].__name__,
                    replaced.__name__,
                )
                continue

            replacements[replaced] = module

        return replacements

    def _drop_replacement_cycles(
        self, replacements: dict[type[MVTModule], type[MVTModule]]
    ) -> None:
        """Undo the replacements between modules which replace each other."""
        cyclic: set[type[MVTModule]] = set()
        for replaced in replacements:
            walked: list[type[MVTModule]] = []
            module = replaced
            while module in replacements and module not in cyclic:
                if module in walked:
                    cyclic.update(walked[walked.index(module) :])
                    break
                walked.append(module)
                module = replacements[module]

        if not cyclic:
            return

        self.log.warning(
            "Modules %s replace each other in a cycle. None of them replaces "
            "anything and all of them will run.",
            ", ".join(sorted(module.__name__ for module in cyclic)),
        )
        for module in cyclic:
            replacements.pop(module, None)

    def _log_replacement(
        self,
        replaced: type[MVTModule],
        module: type[MVTModule],
        replacement: type[MVTModule],
    ) -> None:
        """Report an applied replacement, and any problem with it."""
        if not issubclass(module, replaced):
            self.log.warning(
                "Module %s replaces module %s but is not a subclass of it. "
                "Its results might not be compatible with what modules "
                "depending on %s expect.",
                module.__name__,
                replaced.__name__,
                replaced.__name__,
            )

        if replaced in module.dependencies:
            self.log.warning(
                "Module %s depends on module %s, which it also replaces. The "
                "dependency cannot be satisfied: a replacement has to produce "
                "that data itself.",
                module.__name__,
                replaced.__name__,
            )

        self.log.info(
            "Module %s from %s replaces module %s from %s.",
            replacement.__name__,
            get_module_origin(replacement).label,
            replaced.__name__,
            get_module_origin(replaced).label,
        )

    def _apply_replacements(
        self, modules: list[type[MVTModule]]
    ) -> list[type[MVTModule]]:
        """Drop the modules superseded by a module declaring `replaces`."""
        declared = self._declared_replacements(modules)
        self._drop_replacement_cycles(declared)

        replacements: dict[type[MVTModule], type[MVTModule]] = {}
        for replaced, module in declared.items():
            # Follow chains of replacements, so that a dependency on a
            # replaced module always resolves to a module which is part of
            # the run.
            replacement = module
            while replacement in declared:
                replacement = declared[replacement]

            # Only the replacements which are applied are reported, so that
            # the record matches the modules which actually run.
            self._log_replacement(replaced, module, replacement)
            replacements[replaced] = replacement

        self.module_replacements = replacements
        return [module for module in modules if module not in replacements]

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

    def _module_dependencies(
        self, module: type[MVTModule]
    ) -> list[tuple[type[MVTModule], type[MVTModule]]]:
        """Return the (declared, resolved) dependencies of a module.

        A dependency on a module which was replaced is resolved to the module
        which took its place. A module which replaces one of its own
        dependencies is not made to depend on itself, while a module which
        declares itself as a dependency is left alone and still fails the
        circular dependency check.
        """
        dependencies = []
        for dependency in module.dependencies:
            resolved = self.module_replacements.get(dependency, dependency)
            if resolved is module and dependency is not module:
                continue
            dependencies.append((dependency, resolved))

        return dependencies

    @staticmethod
    def _dependency_name(
        declared: type[MVTModule], resolved: type[MVTModule]
    ) -> str:
        """Return how a dependency is named in the messages about it.

        A dependency is named as the module which declared it wrote it, and,
        when that module was replaced, as the module which runs in its place.
        """
        if declared is resolved:
            return declared.__name__

        return f"{resolved.__name__} (replacing module {declared.__name__})"

    def _selected_modules(
        self, modules: list[type[MVTModule]]
    ) -> Optional[list[type[MVTModule]]]:
        """Return the modules explicitly requested, or all the enabled ones.

        Returns None when a module was requested by name and no module of
        that name can be run.
        """
        if not self.module_name:
            return [module for module in modules if module.enabled]

        selected = [
            module for module in modules if module.__name__ == self.module_name
        ]

        # A module replacing another one does not have to keep its name, so
        # the name of a replaced module selects its replacement.
        if not selected:
            for replaced, replacement in self.module_replacements.items():
                if replaced.__name__ != self.module_name or replacement in selected:
                    continue
                self.log.info(
                    "Module %s was replaced by module %s, which is run "
                    "in its place.",
                    replaced.__name__,
                    replacement.__name__,
                )
                selected.append(replacement)

        if not selected:
            self.log.warning(
                "No module named %s is available for the %s command. "
                "No modules will be run.",
                self.module_name,
                self.name,
            )
            return None

        return selected

    def _skipped_modules(
        self,
        required: list[type[MVTModule]],
        module_indexes: dict[type[MVTModule], int],
    ) -> dict[type[MVTModule], tuple[type[MVTModule], type[MVTModule]]]:
        """Return the modules to drop because a dependency is unavailable.

        A module declaring a dependency this command cannot provide is unable
        to run, and so is every module depending on it. Dropping only those
        keeps a single wrong declaration - in a module scoped to several
        commands, for example - from silencing an entire analysis.

        The returned mapping gives, for each skipped module, the module which
        is missing a dependency and the dependency it is missing.
        """
        skipped: dict[type[MVTModule], tuple[type[MVTModule], type[MVTModule]]] = {}
        # Skipping the one module a run was asked for leaves nothing to run,
        # which the caller reports instead.
        remainder = (
            "" if self.module_name else " The rest of the analysis will still run."
        )

        # Skipping one module can skip the modules depending on it, which the
        # pass over the module list may already have gone past, so repeat the
        # pass until nothing changes.
        changed = True
        while changed:
            changed = False
            for module in required:
                if module in skipped:
                    continue

                for declared, dependency in self._module_dependencies(module):
                    if dependency not in module_indexes:
                        # A replaced dependency always resolves to a module of
                        # this command, so an unavailable one is always the
                        # module class the author declared.
                        skipped[module] = (module, declared)
                        changed = True
                        self.log.warning(
                            "Module %s will be SKIPPED: it depends on module "
                            "%s, which is not available in this command.%s",
                            module.__name__,
                            declared.__name__,
                            remainder,
                        )
                        break

                    if dependency in skipped:
                        root, missing = skipped[dependency]
                        skipped[module] = (root, missing)
                        changed = True
                        if dependency is root:
                            self.log.warning(
                                "Module %s will be SKIPPED: it depends on "
                                "module %s, itself skipped for depending on "
                                "unavailable module %s.%s",
                                module.__name__,
                                self._dependency_name(declared, dependency),
                                missing.__name__,
                                remainder,
                            )
                        else:
                            self.log.warning(
                                "Module %s will be SKIPPED: it depends on "
                                "skipped module %s, in a chain starting at "
                                "module %s, which depends on unavailable "
                                "module %s.%s",
                                module.__name__,
                                self._dependency_name(declared, dependency),
                                root.__name__,
                                missing.__name__,
                                remainder,
                            )
                        break

        return skipped

    def _ordered_modules(self) -> Optional[list[type[MVTModule]]]:
        """Return enabled modules in stable topological order."""
        modules = self._available_modules()
        module_indexes = {module: index for index, module in enumerate(modules)}

        selected = self._selected_modules(modules)
        if selected is None:
            return None

        required: set[type[MVTModule]] = set()
        pending = list(selected)
        while pending:
            module = pending.pop()
            if module in required:
                continue
            required.add(module)
            for _, dependency in self._module_dependencies(module):
                # Unavailable dependencies are reported by _skipped_modules().
                if dependency in module_indexes:
                    pending.append(dependency)

        ordered_required = sorted(required, key=lambda module: module_indexes[module])
        skipped = self._skipped_modules(ordered_required, module_indexes)
        runnable = [module for module in ordered_required if module not in skipped]
        if skipped and not runnable:
            self.log.warning(
                "Every selected module was skipped for an unavailable "
                "dependency. No modules will be run."
            )
            return None

        dependents: dict[type[MVTModule], list[type[MVTModule]]] = {
            module: [] for module in runnable
        }
        indegree = {module: 0 for module in runnable}
        for module in runnable:
            for _, dependency in self._module_dependencies(module):
                if dependency not in indegree:
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

        if len(ordered) != len(runnable):
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

    def run(self) -> None:
        ordered_modules = self._ordered_modules()
        if ordered_modules is None:
            return

        self._log_loaded_modules(ordered_modules)

        try:
            self.init()
        except NotImplementedError:
            pass

        executed_by_type: dict[type[MVTModule], MVTModule] = {}
        for module in ordered_modules:

            module_logger = get_module_logger(module)

            m = module(
                target_path=self.target_path,
                results_path=self.results_path,
                module_options=self.module_options,
                log=module_logger,
            )
            # Dependencies are keyed by the module class they declare, even
            # when it was replaced, so that a module asking for the results
            # of a replaced module receives those of its replacement.
            m.dependency_modules = {
                dependency: executed_by_type[resolved]
                for dependency, resolved in self._module_dependencies(module)
            }

            if self.iocs.total_ioc_count:
                m.indicators = self.iocs
                m.indicators.log = m.log

            if self.serial:
                m.serial = self.serial

            try:
                self.module_init(m)
            except NotImplementedError:
                pass

            try:
                run_module(m)
            except EncryptedBackupError:
                self.log.critical(
                    "The backup appears to be encrypted. "
                    "Please decrypt it first using `mvt-ios decrypt-backup`."
                )
                return

            self.executed.append(m)
            executed_by_type[module] = m
            self.timeline.extend(m.timeline)
            self.url_results.extend(m.url_results)
            self.alertstore.extend(m.alertstore.alerts)

        try:
            self.finish()
        except NotImplementedError:
            pass

        # We only store the timeline from the parent/main command
        if self.sub_command:
            return

        self._store_timeline()
        self._store_alerts_timeline()
        self._store_alerts()
        self._store_urls()
        self._store_info()
