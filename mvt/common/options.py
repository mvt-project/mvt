# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

# From: https://gist.github.com/stanchan/bce1c2d030c76fe9223b5ff6ad0f03db

from click import Option, UsageError


class MutuallyExclusiveOption(Option):
    """This class extends click to support mutually exclusive options."""

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        help_msg = kwargs.get("help", "")
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = (
                f"{help_msg} NOTE: This argument is mutually exclusive with arguments"
                f"[{ex_str}]."
            )

        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise UsageError(
                f"Illegal usage: `{self.name}` is mutually exclusive "
                f"with arguments `{', '.join(self.mutually_exclusive)}`."
            )

        return super().handle_parse_result(ctx, opts, args)
