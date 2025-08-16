# pxos/llm/tools.py - Safe tools registry with validation
import jsonschema

class ToolRegistry:
    def __init__(self, caps):
        self._caps = caps
        self._funcs = {
            "open_map": {
                "cap": "tools",
                "schema": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                        "zoom": {"type": "integer", "minimum": 0, "maximum": 22}
                    },
                    "required": ["lat", "lon"]
                },
                "fn": self._open_map
            },
            "bitpack_encode": {
                "cap": "tools",
                "schema": {
                    "type": "object",
                    "properties": {
                        "lang_id": {"type": "string", "maxLength": 8},
                        "payload": {"type": "string", "maxLength": 1000000}
                    },
                    "required": ["lang_id", "payload"]
                },
                "fn": self._bitpack_encode
            },
        }

    def call(self, name, args):
        spec = self._funcs.get(name)
        if not spec:
            return {"error": "unknown_tool"}

        if not self._caps.get(spec["cap"], False):
            return {"error": "forbidden"}

        try:
            jsonschema.validate(args, spec["schema"])
        except jsonschema.ValidationError as e:
            return {"error": "invalid_args", "details": str(e)}

        return spec["fn"](args)

    # Stub implementations
    def _open_map(self, args):
        pass

    def _bitpack_encode(self, args):
        pass
