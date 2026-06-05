# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging

from mvt.common.command import Command
from mvt.common.module import MVTModule


class RecordingModule(MVTModule):
    run_order = []

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
