# Output schemas

MVT validates its JSON output with versioned Pydantic models. The schema version
used for a run is recorded as `output_schema_version` in `info.json`.

MVT preserves the established on-disk format: most module files contain an array
of result objects, while modules whose results are naturally grouped contain an
object keyed by source or namespace. Detection files and `alerts.json` contain
arrays of alert objects. Timestamps remain strings because their timezone and
precision depend on the source artifact.

## Exporting JSON Schema

Both platform commands can print a versioned JSON Schema bundle:

```bash
mvt-ios schemas
mvt-android schemas
```

Use `--output` to write one Draft 2020-12 JSON Schema file for each output:

```bash
mvt-ios schemas --output ./mvt-ios-schemas
mvt-android schemas --output ./mvt-android-schemas
```

## Python API

Models and schema discovery functions are available from `mvt.schemas`:

```python
from mvt.schemas import get_output_model

SafariHistoryOutput = get_output_model("safari_history", platform="ios")
validated = SafariHistoryOutput.model_validate(records)
json_schema = SafariHistoryOutput.model_json_schema()
```

Common outputs have dedicated field-level models. Built-in module outputs have a
declared root shape, and modules with an established dedicated record model expose
its complete field schema.

## Custom modules

Custom modules can publish a precise contract by assigning a Pydantic root model
to `output_model`:

```python
from pydantic import BaseModel, RootModel

from mvt.common.module import MVTModule


class ExampleRecord(BaseModel):
    message: str
    timestamp: str | None = None


class ExampleOutput(RootModel[list[ExampleRecord]]):
    pass


class ExampleModule(MVTModule):
    output_model = ExampleOutput
```

For compatibility, a custom module without `output_model` can still write an
array or object containing JSON values. MVT logs a warning when it uses this
generic contract. A future major release may require custom modules to declare
their output models.

## Compatibility policy

Within one output schema major version, required fields are not removed and field
types are not narrowed. New optional fields may be added. A breaking output
change requires a new schema major version and a migration note.
