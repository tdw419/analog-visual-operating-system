# validate_hlir.py
import jsonschema
from pxos_ops_schema import SCHEMA

class ValidationError(Exception):
    pass

def validate_hlir(hlir: dict) -> None:
    try:
        jsonschema.validate(hlir, SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Schema validation failed: {e.message}")