# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
# https://license.mvt.re/1.1/

from io import StringIO

from mvt.common.password import _readline_with_asterisks


def test_readline_with_asterisks():
    output = StringIO()

    password = _readline_with_asterisks(
        output, StringIO("pass\x7fword\n"), "Enter backup password: "
    )

    assert password == "pasword"
    assert output.getvalue() == "Enter backup password: ****\b \b****"


def test_readline_with_asterisks_ignores_nul_and_handles_eof():
    output = StringIO()

    password = _readline_with_asterisks(output, StringIO("a\x00b\x04\x04"), "")

    assert password == "ab"
    assert output.getvalue() == "**"
