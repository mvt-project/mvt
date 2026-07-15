# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import threading
import time
from io import StringIO

from rich.console import Console

from mvt.common.command import Command
from mvt.common.config import settings
from mvt.common.log import MVTLogHandler
from mvt.common.module import EncryptedBackupError, MVTModule


class RecordingModule(MVTModule):
    run_order: list[str] = []

    def run(self):
        self.run_order.append(self.__class__.__name__)

    def check_indicators(self):
        pass


class FirstModule(RecordingModule):
    def run(self):
        super().run()
        self.results = ["first"]


class SecondModule(RecordingModule):
    dependencies = (FirstModule,)

    def run(self):
        super().run()
        self.results = self.get_dependency_results(FirstModule) + ["second"]


class ThirdModule(RecordingModule):
    dependencies = (SecondModule,)


class IndependentModule(RecordingModule):
    pass


class CustomIOSBackupModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)


class CustomIOSFSModule(RecordingModule):
    supported_commands = (("ios", "check-fs"),)


class CustomDependsOnBuiltin(RecordingModule):
    supported_commands = (("ios", "check-backup"),)
    dependencies = (FirstModule,)


class RecordingCommand(Command):
    def init(self):
        self.initialized = True

    def module_init(self, module):
        pass

    def finish(self):
        pass


class TestCommand:
    def setup_method(self):
        RecordingModule.run_order = []

    def test_store_alerts_handles_bytes(self, tmp_path):
        cmd = Command(results_path=str(tmp_path))
        cmd.alertstore.medium(
            "bytes event",
            "",
            {"payload": b"\xa8\xa9"},
        )

        cmd._store_alerts()

        alerts = json.loads((tmp_path / "alerts.json").read_text())
        assert alerts[0]["event"]["payload"] == "\\xa8\\xa9"

    def test_timeline_deduplication_preserves_first_seen_order(self):
        timeline = [
            {"timestamp": "same", "event": "first"},
            {"timestamp": "same", "event": "second"},
            {"timestamp": "same", "event": "first"},
        ]

        assert MVTModule._deduplicate_timeline(timeline) == timeline[:2]

    def test_modules_run_in_stable_topological_order(self):
        cmd = RecordingCommand(jobs=1)
        cmd.modules = [ThirdModule, IndependentModule, SecondModule, FirstModule]

        cmd.run()

        assert RecordingModule.run_order == [
            "IndependentModule",
            "FirstModule",
            "SecondModule",
            "ThirdModule",
        ]
        second = next(module for module in cmd.executed if isinstance(module, SecondModule))
        assert second.results == ["first", "second"]

    def test_selected_module_runs_transitive_dependencies(self):
        cmd = RecordingCommand(module_name="ThirdModule", jobs=1)
        cmd.modules = [ThirdModule, SecondModule, FirstModule, IndependentModule]

        cmd.run()

        assert RecordingModule.run_order == [
            "FirstModule",
            "SecondModule",
            "ThirdModule",
        ]

    def test_circular_dependency_warns_and_stops(self, caplog):
        class CircularOne(RecordingModule):
            pass

        class CircularTwo(RecordingModule):
            dependencies = (CircularOne,)

        CircularOne.dependencies = (CircularTwo,)

        cmd = RecordingCommand()
        cmd.modules = [CircularOne, CircularTwo]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == []
        assert not hasattr(cmd, "initialized")
        assert "Circular module dependency detected" in caplog.text

    def test_unavailable_dependency_warns_and_stops(self, caplog):
        class UnavailableModule(RecordingModule):
            pass

        class DependentModule(RecordingModule):
            dependencies = (UnavailableModule,)

        cmd = RecordingCommand()
        cmd.modules = [DependentModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == []
        assert not hasattr(cmd, "initialized")
        assert "depends on unavailable module UnavailableModule" in caplog.text

    def test_custom_modules_are_filtered_before_ordering(self):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [CustomIOSBackupModule, CustomIOSFSModule]

        assert [module.__name__ for module in cmd._ordered_modules()] == [
            "FirstModule",
            "CustomIOSBackupModule",
        ]

    def test_selected_custom_module_runs(self):
        cmd = RecordingCommand(module_name="CustomIOSBackupModule", jobs=1)
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.custom_modules = [CustomIOSBackupModule]

        cmd.run()

        assert RecordingModule.run_order == ["CustomIOSBackupModule"]

    def test_selected_unsupported_custom_module_does_not_run(self):
        cmd = RecordingCommand(module_name="CustomIOSFSModule")
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.custom_modules = [CustomIOSFSModule]

        cmd.run()

        assert RecordingModule.run_order == []

    def test_custom_module_dependencies_use_topological_order(self):
        cmd = RecordingCommand(module_name="CustomDependsOnBuiltin", jobs=1)
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [SecondModule, FirstModule]
        cmd.custom_modules = [CustomDependsOnBuiltin]

        cmd.run()

        assert RecordingModule.run_order == ["FirstModule", "CustomDependsOnBuiltin"]

    def test_parallel_modules_overlap_and_respect_worker_limit(self):
        lock = threading.Lock()
        barrier = threading.Barrier(2)
        active = 0
        maximum = 0
        overlapped = []

        class ParallelModule(RecordingModule):
            def run(self):
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                try:
                    barrier.wait(timeout=2)
                    overlapped.append(self.__class__.__name__)
                    time.sleep(0.02)
                finally:
                    with lock:
                        active -= 1

        class ParallelOne(ParallelModule):
            pass

        class ParallelTwo(ParallelModule):
            pass

        class ParallelThree(ParallelModule):
            pass

        cmd = RecordingCommand(jobs=2)
        cmd.modules = [ParallelOne, ParallelTwo, ParallelThree]
        cmd.run()

        assert maximum == 2
        assert {"ParallelOne", "ParallelTwo"}.issubset(overlapped)

    def test_dependencies_wait_and_transitive_dependencies_run_once(self):
        prerequisite_finished = threading.Event()
        runs = []

        class Prerequisite(RecordingModule):
            def run(self):
                runs.append("prerequisite")
                self.results = ["ready"]
                prerequisite_finished.set()

        class Dependent(RecordingModule):
            dependencies = (Prerequisite,)

            def run(self):
                assert prerequisite_finished.is_set()
                assert self.get_dependency_results(Prerequisite) == ["ready"]
                runs.append(self.__class__.__name__)

        class DependentOne(Dependent):
            pass

        class DependentTwo(Dependent):
            pass

        cmd = RecordingCommand(jobs=3)
        cmd.modules = [DependentOne, DependentTwo, Prerequisite]
        cmd.run()

        assert runs.count("prerequisite") == 1
        assert set(runs[1:]) == {"DependentOne", "DependentTwo"}

    def test_parallel_unsafe_module_runs_exclusively(self):
        lock = threading.Lock()
        active = 0
        unsafe_ran_exclusively = []

        class SafeOne(RecordingModule):
            def run(self):
                nonlocal active
                with lock:
                    active += 1
                time.sleep(0.03)
                with lock:
                    active -= 1

        class Unsafe(RecordingModule):
            parallel_safe = False

            def run(self):
                nonlocal active
                with lock:
                    unsafe_ran_exclusively.append(active == 0)
                    active += 1
                time.sleep(0.01)
                with lock:
                    active -= 1

        class SafeTwo(SafeOne):
            pass

        cmd = RecordingCommand(jobs=3)
        cmd.modules = [SafeOne, Unsafe, SafeTwo]
        cmd.run()

        assert unsafe_ran_exclusively == [True]

    def test_results_are_aggregated_in_topological_order(self):
        release_first = threading.Event()

        class SlowFirst(RecordingModule):
            def run(self):
                release_first.wait(timeout=2)
                self.results = ["first"]
                self.timeline = [{"module": "first"}]
                self.alertstore.info("first", "", {"order": 1})

        class FastSecond(RecordingModule):
            def run(self):
                self.results = ["second"]
                self.timeline = [{"module": "second"}]
                self.alertstore.info("second", "", {"order": 2})
                release_first.set()

        cmd = RecordingCommand(jobs=2)
        cmd.modules = [SlowFirst, FastSecond]
        cmd.run()

        assert [type(module) for module in cmd.executed] == [SlowFirst, FastSecond]
        assert [entry["module"] for entry in cmd.timeline] == ["first", "second"]
        assert [alert.message for alert in cmd.alertstore.alerts] == ["first", "second"]

    def test_parallel_console_logs_are_grouped_and_file_log_is_complete(
        self, tmp_path
    ):
        output = StringIO()
        handler = MVTLogHandler(
            console=Console(file=output, force_terminal=False, color_system=None)
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger("mvt")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        release_slow = threading.Event()

        class SlowLog(RecordingModule):
            def run(self):
                self.log.info("slow-a")
                release_slow.wait(timeout=2)
                self.log.info("slow-b")

        class FastLog(RecordingModule):
            def run(self):
                self.log.info("fast-a")
                self.log.info("fast-b")
                release_slow.set()

        SlowLog.__module__ = "mvt.tests.parallel"
        FastLog.__module__ = "mvt.tests.parallel"
        try:
            cmd = RecordingCommand(results_path=str(tmp_path), jobs=2)
            cmd.modules = [SlowLog, FastLog]
            cmd.run()
        finally:
            logger.removeHandler(handler)

        console_output = output.getvalue()
        assert console_output.index("--- FastLog ---") < console_output.index(
            "--- SlowLog ---"
        )
        assert console_output.index("fast-a") < console_output.index("fast-b")
        assert "slow-a" in console_output and "slow-b" in console_output
        file_output = (tmp_path / "command.log").read_text()
        for message in ("slow-a", "slow-b", "fast-a", "fast-b"):
            assert message in file_output

    def test_encrypted_backup_stops_scheduling_and_cleans_up(self, caplog):
        finish_called = []

        class Encrypted(RecordingModule):
            def run(self):
                raise EncryptedBackupError

        class NeverScheduled(RecordingModule):
            dependencies = (Encrypted,)

        class CleanupCommand(RecordingCommand):
            def finish(self):
                finish_called.append(True)

        cmd = CleanupCommand(jobs=2)
        cmd.modules = [Encrypted, NeverScheduled]
        with caplog.at_level(logging.CRITICAL):
            cmd.run()

        assert finish_called == [True]
        assert not any(isinstance(module, NeverScheduled) for module in cmd.executed)
        assert "backup appears to be encrypted" in caplog.text

    def test_profiling_forces_sequential_execution(self, monkeypatch, caplog):
        run_order = []

        class ProfileOne(RecordingModule):
            def run(self):
                run_order.append("one")

        class ProfileTwo(RecordingModule):
            def run(self):
                run_order.append("two")

        monkeypatch.setattr(settings, "PROFILE", True)
        cmd = RecordingCommand(jobs=4)
        cmd.modules = [ProfileOne, ProfileTwo]
        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert run_order == ["one", "two"]
        assert "forcing sequential module execution" in caplog.text
