# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging

from mvt.common.command import Command
from mvt.common.module import MVTModule


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


class URLRecordingModule(RecordingModule):
    def collect_url_results(self):
        self.add_url_result(
            "https://example.org/message",
            "2026-07-29 12:00:00.000000",
            "test-chat",
        )


class CustomIOSBackupModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)


class CustomIOSFSModule(RecordingModule):
    supported_commands = (("ios", "check-fs"),)


class UnscopedCustomModule(RecordingModule):
    pass


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

    def test_stores_collected_urls(self, tmp_path):
        cmd = RecordingCommand(results_path=str(tmp_path))
        cmd.modules = [URLRecordingModule]

        cmd.run()

        assert json.loads((tmp_path / "urls.json").read_text()) == [
            {
                "url": "https://example.org/message",
                "expanded_url": None,
                "timestamp": "2026-07-29 12:00:00.000000",
                "source": "test-chat",
            }
        ]

    def test_modules_run_in_stable_topological_order(self):
        cmd = RecordingCommand()
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
        cmd = RecordingCommand(module_name="ThirdModule")
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

    def test_unavailable_dependency_only_skips_the_dependent_module(self, caplog):
        class UnavailableModule(RecordingModule):
            pass

        class DependentModule(RecordingModule):
            dependencies = (UnavailableModule,)

        cmd = RecordingCommand()
        cmd.modules = [DependentModule, IndependentModule, FirstModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == ["IndependentModule", "FirstModule"]
        assert cmd.initialized
        assert "Module DependentModule will be SKIPPED" in caplog.text
        assert "depends on module UnavailableModule" in caplog.text

    def test_modules_depending_on_a_skipped_module_are_skipped_too(self, caplog):
        class UnavailableModule(RecordingModule):
            pass

        class SkippedModule(RecordingModule):
            dependencies = (UnavailableModule,)

        class DependsOnSkippedModule(RecordingModule):
            dependencies = (SkippedModule,)

        class DependsOnTheChain(RecordingModule):
            dependencies = (DependsOnSkippedModule,)

        cmd = RecordingCommand()
        cmd.modules = [
            DependsOnTheChain,
            DependsOnSkippedModule,
            SkippedModule,
            IndependentModule,
        ]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == ["IndependentModule"]
        skip_warnings = [
            record.getMessage()
            for record in caplog.records
            if "will be SKIPPED" in record.getMessage()
        ]
        assert len(skip_warnings) == 3
        assert [warning.split()[1] for warning in skip_warnings] == [
            "SkippedModule",
            "DependsOnSkippedModule",
            "DependsOnTheChain",
        ]
        # Every warning names the root cause: the module missing a dependency
        # and the dependency it is missing.
        assert all("UnavailableModule" in warning for warning in skip_warnings)
        assert all("module SkippedModule" in warning for warning in skip_warnings[1:])

    def test_explicitly_selected_module_with_missing_dependency_runs_nothing(
        self, caplog
    ):
        class UnavailableModule(RecordingModule):
            pass

        class DependentModule(RecordingModule):
            dependencies = (UnavailableModule,)

        cmd = RecordingCommand(module_name="DependentModule")
        cmd.modules = [DependentModule, IndependentModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == []
        assert "Module DependentModule will be SKIPPED" in caplog.text
        assert "No modules will be run" in caplog.text
        # Nothing else was selected, so the warning must not promise that the
        # analysis continues right before saying that it does not.
        assert "The rest of the analysis will still run" not in caplog.text

    def test_unaffected_dependency_chains_keep_their_order(self, caplog):
        class UnavailableModule(RecordingModule):
            pass

        class SkippedModule(RecordingModule):
            dependencies = (UnavailableModule,)

        cmd = RecordingCommand()
        cmd.modules = [ThirdModule, SkippedModule, SecondModule, FirstModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == [
            "FirstModule",
            "SecondModule",
            "ThirdModule",
        ]

    def test_custom_modules_are_filtered_before_ordering(self):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [
            CustomIOSBackupModule,
            CustomIOSFSModule,
            UnscopedCustomModule,
        ]

        assert [module.__name__ for module in cmd._ordered_modules()] == [
            "FirstModule",
            "CustomIOSBackupModule",
        ]

    def test_selected_custom_module_runs(self):
        cmd = RecordingCommand(module_name="CustomIOSBackupModule")
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
        cmd = RecordingCommand(module_name="CustomDependsOnBuiltin")
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [SecondModule, FirstModule]
        cmd.custom_modules = [CustomDependsOnBuiltin]

        cmd.run()

        assert RecordingModule.run_order == ["FirstModule", "CustomDependsOnBuiltin"]
