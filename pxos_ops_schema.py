# pxos_ops_schema.py
# pxos-ops/1.0 — coverage for: RECT, COMMIT, SLEEP, SYNC_ROW, DAC_WRITE, INTEGRATE, FILTER, MULTIPLY, SUM
SCHEMA = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pxos.io/schema/ops/1.0",
  "title": "PXOS Operations",
  "type": "object",
  "required": ["schemaVersion", "program"],
  "additionalProperties": False,
  "properties": {
    "schemaVersion": {"type": "string", "const": "pxos-ops/1.0"},
    "meta": {"type": "object"},
    "program": {
      "type": "array",
      "items": {
        "oneOf": [
          { "type": "object", "additionalProperties": False,
            "properties": {"op": {"const": "COMMIT"}}, "required": ["op"] },

          { "type": "object", "additionalProperties": False,
            "properties": {"op": {"const": "SLEEP"}, "ms": {"type": "integer", "minimum": 0}},
            "required": ["op","ms"] },

          { "type": "object", "additionalProperties": False,
            "properties": {"op": {"const": "SYNC_ROW"}, "i": {"type": "integer", "minimum": 0}},
            "required": ["op","i"] },

          { "type": "object", "additionalProperties": False,
            "properties": {
              "op": {"const": "DAC_WRITE"},
              "ch": {"type": "integer", "minimum": 0, "maximum": 31},
              "val": {"type": "integer", "minimum": 0, "maximum": 65535}
            },
            "required": ["op","ch","val"] },

          { "type": "object", "additionalProperties": False,
            "properties": {
              "op": {"const": "RECT"},
              "x": {"type": "integer", "minimum": 0}, "y": {"type": "integer", "minimum": 0},
              "w": {"type": "integer", "minimum": 0}, "h": {"type": "integer", "minimum": 0},
              "r": {"type": "integer", "minimum": 0, "maximum": 255},
              "g": {"type": "integer", "minimum": 0, "maximum": 255},
              "b": {"type": "integer", "minimum": 0, "maximum": 255}
            },
            "required": ["op","x","y","w","h","r","g","b"] },

          { "type": "object", "additionalProperties": False,
            "properties": {
              "op": {"const": "INTEGRATE"},
              "tau": {"type": "number", "exclusiveMinimum": 0},
              "src": {"type": "integer"}, "dst": {"type": "integer"}
            },
            "required": ["op","tau","src","dst"] },

          { "type": "object", "additionalProperties": False,
            "properties": {
              "op": {"const": "FILTER"},
              "type": {"type": "string"},     # e.g., "lp","hp","bp"
              "fc": {"type": "integer", "minimum": 0},
              "src": {"type": "integer"}, "dst": {"type": "integer"}
            },
            "required": ["op","type","fc","src","dst"] },

          { "type": "object", "additionalProperties": False,
            "properties": {
              "op": {"const": "MULTIPLY"},
              "gain": {"type": "number"},
              "src": {"type": "integer"}, "dst": {"type": "integer"}
            },
            "required": ["op","gain","src","dst"] },

          { "type": "object", "additionalProperties": False,
            "properties": {
              "op": {"const": "SUM"},
              "inputs": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 1
              },
              "output": {"type": "integer"}
            },
            "required": ["op","inputs","output"] }
        ]
      }
    }
  }
}