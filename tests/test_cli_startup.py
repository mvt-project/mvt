# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import pytest

from .plugin_fixtures import run_isolated_python

# Importing a platform CLI must only build its command tree: the console
# scripts import it before Click can answer a shell completion request, which
# the completion scripts make on every keystroke. Every command imports what
# it runs when it is invoked. Each of these costs tens of milliseconds to
# import and is the sign that a command implementation is imported too early.
HEAVY_MODULES = ("pydantic", "requests", "Crypto", "mvt.common.module")


@pytest.mark.parametrize("cli_module", ("mvt.ios.cli", "mvt.android.cli"))
def test_importing_a_cli_does_not_import_the_module_machinery(cli_module, tmp_path):
    result = run_isolated_python(
        "import sys\n"
        f"import {cli_module}\n"
        f"print(','.join(name for name in {HEAVY_MODULES!r} if name in sys.modules))\n",
        home=tmp_path / "home",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", f"{cli_module} imported {result.stdout.strip()}"
