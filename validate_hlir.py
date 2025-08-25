import jsonschema
from pxos_schema import SCHEMA
from pxos_sync_engine import ValidationError

def validate_hlir(hlir: dict) -> None:
    try:
        jsonschema.validate(hlir, SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Schema validation failed: {e.message}")
