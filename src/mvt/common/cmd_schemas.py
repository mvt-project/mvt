# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Shared implementation for the platform schema-export commands."""

import json
from typing import Optional

import click

from mvt.schemas import export_json_schemas, schema_bundle


def emit_schemas(platform: str, output: Optional[str]) -> None:
    if output:
        paths = export_json_schemas(output, platform)
        click.echo(f"Exported {len(paths)} {platform} output schemas to {output}")
        return

    click.echo(json.dumps(schema_bundle(platform), indent=2))
