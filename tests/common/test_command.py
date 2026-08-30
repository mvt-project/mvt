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


class ReplacementModule(FirstModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = FirstModule

    def run(self):
        super().run()
        self.results = ["replacement"]


class OtherReplacementModule(FirstModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = FirstModule


class UnrelatedReplacementModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = IndependentModule


class ReplacementOfReplacementModule(ReplacementModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = ReplacementModule

    def run(self):
        super().run()
        self.results = ["replacement of replacement"]


class ReplacesOwnDependencyModule(FirstModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = FirstModule
    dependencies = (FirstModule,)


class DisabledReplacementModule(FirstModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = FirstModule
    enabled = False


class MutualReplacementOne(RecordingModule):
    supported_commands = (("ios", "check-backup"),)


class MutualReplacementTwo(RecordingModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = MutualReplacementOne


MutualReplacementOne.replaces = MutualReplacementTwo


class CycleOneModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)


class CycleTwoModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = CycleOneModule


class CycleThreeModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = CycleTwoModule


CycleOneModule.replaces = CycleThreeModule


class UnavailableDependencyModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)


class ReplacementMissingDependency(FirstModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = FirstModule
    dependencies = (UnavailableDependencyModule,)


class SharedSlugModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)
    slug = "shared_slug"


class OtherSharedSlugModule(RecordingModule):
    supported_commands = (("ios", "check-backup"),)
    slug = "shared_slug"


class ReplacementKeepingTheSlug(FirstModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = FirstModule
    slug = "first_module"


class SameNameReplacementModule(FirstModule):
    supported_commands = (("ios", "check-backup"),)
    replaces = FirstModule

    def run(self):
        super().run()
        self.results = ["replacement"]


# Modules replacing a built-in one usually keep its class name, which is the
# name `--module` matches on.
SameNameReplacementModule.__name__ = "FirstModule"


def logged_substitutions(caplog) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.INFO and "replaces module" in record.getMessage()
    ]


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

    def test_custom_module_replaces_builtin(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule, IndependentModule]
        cmd.custom_modules = [ReplacementModule]

        with caplog.at_level(logging.INFO):
            cmd.run()

        assert RecordingModule.run_order == ["IndependentModule", "ReplacementModule"]
        assert cmd.module_replacements == {FirstModule: ReplacementModule}
        assert (
            "Module ReplacementModule from" in caplog.text
            and "replaces module FirstModule" in caplog.text
        )

    def test_modules_without_replaces_all_run(self):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [CustomIOSBackupModule]

        cmd.run()

        assert RecordingModule.run_order == ["FirstModule", "CustomIOSBackupModule"]
        assert cmd.module_replacements == {}

    def test_unavailable_replaced_module_is_ignored(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [IndependentModule]
        cmd.custom_modules = [ReplacementModule]

        with caplog.at_level(logging.INFO):
            cmd.run()

        assert RecordingModule.run_order == ["IndependentModule", "ReplacementModule"]
        assert cmd.module_replacements == {}
        assert "replaces module FirstModule" not in caplog.text

    def test_dependencies_are_resolved_to_the_replacement(self):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [SecondModule, FirstModule]
        cmd.custom_modules = [ReplacementModule]

        cmd.run()

        assert RecordingModule.run_order == ["ReplacementModule", "SecondModule"]
        second = next(
            module for module in cmd.executed if isinstance(module, SecondModule)
        )
        assert isinstance(second.dependency_modules[FirstModule], ReplacementModule)
        assert second.results == ["replacement", "second"]

    def test_replacement_with_unavailable_dependency_skips_its_dependents(
        self, caplog
    ):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule, SecondModule, IndependentModule]
        cmd.custom_modules = [ReplacementMissingDependency]

        with caplog.at_level(logging.INFO):
            cmd.run()

        # The replacement cannot run, and the module it replaced was dropped
        # from the run by the replacement, so neither of them produces
        # results and the module depending on the replaced one is skipped.
        assert RecordingModule.run_order == ["IndependentModule"]
        assert (
            "Module ReplacementMissingDependency will be SKIPPED: it depends "
            "on module UnavailableDependencyModule, which is not available in "
            "this command." in caplog.text
        )
        # The skipped dependent is told which module it actually depends on,
        # and the module class its author declared.
        assert (
            "Module SecondModule will be SKIPPED: it depends on module "
            "ReplacementMissingDependency (replacing module FirstModule), "
            "itself skipped for depending on unavailable module "
            "UnavailableDependencyModule." in caplog.text
        )

    def test_selected_replacement_with_unavailable_dependency_runs_nothing(
        self, caplog, tmp_path
    ):
        cmd = RecordingCommand(module_name="FirstModule", results_path=str(tmp_path))
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule, IndependentModule]
        cmd.custom_modules = [ReplacementMissingDependency]

        with caplog.at_level(logging.INFO):
            cmd.run()

        assert RecordingModule.run_order == []
        assert not hasattr(cmd, "initialized")
        assert (
            "Module FirstModule was replaced by module "
            "ReplacementMissingDependency, which is run in its place."
            in caplog.text
        )
        assert "Module ReplacementMissingDependency will be SKIPPED" in caplog.text
        assert "No modules will be run" in caplog.text
        # Nothing else was selected, so the warnings must not promise that the
        # analysis continues right before saying that it does not.
        assert "The rest of the analysis will still run" not in caplog.text
        # No module ran, so no results were stored next to the command log.
        assert [path.name for path in tmp_path.iterdir()] == ["command.log"]

    def test_chained_replacements_are_resolved(self):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [SecondModule, FirstModule]
        cmd.custom_modules = [ReplacementModule, ReplacementOfReplacementModule]

        cmd.run()

        assert RecordingModule.run_order == [
            "ReplacementOfReplacementModule",
            "SecondModule",
        ]
        second = next(
            module for module in cmd.executed if isinstance(module, SecondModule)
        )
        assert second.results == ["replacement of replacement", "second"]

    def test_replacement_which_is_not_a_subclass_warns(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [IndependentModule]
        cmd.custom_modules = [UnrelatedReplacementModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == ["UnrelatedReplacementModule"]
        assert "is not a subclass of it" in caplog.text

    def test_multiple_modules_replacing_the_same_module_warn(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [ReplacementModule, OtherReplacementModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == [
            "ReplacementModule",
            "OtherReplacementModule",
        ]
        assert cmd.module_replacements == {FirstModule: ReplacementModule}
        assert (
            "Modules ReplacementModule and OtherReplacementModule both replace "
            "module FirstModule. Both of them will run, FirstModule will not, "
            "and modules depending on FirstModule will use the results of "
            "ReplacementModule." in caplog.text
        )
        assert "overwrite each other's results file" in caplog.text

    def test_module_replacing_its_own_dependency_runs(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [ReplacesOwnDependencyModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == ["ReplacesOwnDependencyModule"]
        assert (
            "Module ReplacesOwnDependencyModule depends on module FirstModule, "
            "which it also replaces" in caplog.text
        )

    def test_literal_self_dependency_is_still_circular(self, caplog):
        class SelfDependentModule(RecordingModule):
            pass

        SelfDependentModule.dependencies = (SelfDependentModule,)

        cmd = RecordingCommand()
        cmd.modules = [SelfDependentModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == []
        assert not hasattr(cmd, "initialized")
        assert "Circular module dependency detected" in caplog.text

    def test_disabled_replacement_keeps_the_replaced_module(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [DisabledReplacementModule]

        with caplog.at_level(logging.INFO):
            cmd.run()

        assert RecordingModule.run_order == ["FirstModule"]
        assert cmd.module_replacements == {}
        assert logged_substitutions(caplog) == []

    def test_modules_replacing_each_other_all_run(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.custom_modules = [MutualReplacementOne, MutualReplacementTwo]

        with caplog.at_level(logging.INFO):
            cmd.run()

        assert RecordingModule.run_order == [
            "MutualReplacementOne",
            "MutualReplacementTwo",
        ]
        assert cmd.module_replacements == {}
        assert (
            "Modules MutualReplacementOne, MutualReplacementTwo replace each "
            "other in a cycle" in caplog.text
        )
        assert logged_substitutions(caplog) == []

    def test_replacement_cycle_of_three_modules_all_run(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.custom_modules = [CycleOneModule, CycleTwoModule, CycleThreeModule]

        with caplog.at_level(logging.INFO):
            cmd.run()

        assert RecordingModule.run_order == [
            "CycleOneModule",
            "CycleTwoModule",
            "CycleThreeModule",
        ]
        assert cmd.module_replacements == {}
        assert (
            "Modules CycleOneModule, CycleThreeModule, CycleTwoModule replace "
            "each other in a cycle" in caplog.text
        )
        assert logged_substitutions(caplog) == []

    def test_selected_replaced_module_name_runs_the_replacement(self, caplog):
        cmd = RecordingCommand(module_name="FirstModule")
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [ReplacementModule]

        with caplog.at_level(logging.INFO):
            cmd.run()

        assert RecordingModule.run_order == ["ReplacementModule"]
        assert (
            "Module FirstModule was replaced by module ReplacementModule"
            in caplog.text
        )

    def test_unknown_selected_module_warns_and_stops(self, caplog):
        cmd = RecordingCommand(module_name="NoSuchModule")
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == []
        assert not hasattr(cmd, "initialized")
        assert (
            "No module named NoSuchModule is available for the check-backup "
            "command" in caplog.text
        )

    def test_selected_module_name_matches_the_replacement(self):
        cmd = RecordingCommand(module_name="FirstModule")
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [SameNameReplacementModule]

        cmd.run()

        assert len(cmd.executed) == 1
        assert isinstance(cmd.executed[0], SameNameReplacementModule)
        assert cmd.executed[0].results == ["replacement"]

    def test_list_modules_reflects_replacements(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule, IndependentModule]
        cmd.custom_modules = [ReplacementModule]

        with caplog.at_level(logging.INFO):
            cmd.list_modules()

        listed = [
            record.getMessage()
            for record in caplog.records
            if "Modules from" in record.getMessage()
        ]
        assert any("ReplacementModule" in message for message in listed)
        assert not any("FirstModule" in message for message in listed)

    def test_modules_sharing_a_slug_are_reported(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.custom_modules = [SharedSlugModule, OtherSharedSlugModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert RecordingModule.run_order == [
            "SharedSlugModule",
            "OtherSharedSlugModule",
        ]
        collisions = [
            record.getMessage()
            for record in caplog.records
            if "both use the slug" in record.getMessage()
        ]
        assert len(collisions) == 1
        assert "Modules SharedSlugModule from" in collisions[0]
        assert "and OtherSharedSlugModule from" in collisions[0]
        assert "both use the slug shared_slug" in collisions[0]
        assert "overwrites the results of the other in shared_slug.json" in (
            collisions[0]
        )

    def test_replacement_keeping_the_replaced_slug_is_not_reported(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule]
        cmd.custom_modules = [ReplacementKeepingTheSlug]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        # The replaced module is no longer part of the run, so taking over its
        # slug is what the replacement is for, not a collision.
        assert RecordingModule.run_order == ["ReplacementKeepingTheSlug"]
        assert ReplacementKeepingTheSlug.get_slug() == FirstModule.get_slug()
        assert "both use the slug" not in caplog.text

    def test_modules_with_distinct_slugs_are_not_reported(self, caplog):
        cmd = RecordingCommand()
        cmd.platform = "ios"
        cmd.name = "check-backup"
        cmd.modules = [FirstModule, IndependentModule]
        cmd.custom_modules = [CustomIOSBackupModule]

        with caplog.at_level(logging.WARNING):
            cmd.run()

        assert "both use the slug" not in caplog.text
