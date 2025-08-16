# pxos/runtimes/llm_process.py - Complete LLM application
from .base import Process
from ..hostcalls_llm import LlmRequest, HostCallsLLM, LlmChunk
from ..llm.adapter import LlmAdapter
from ..llm.tools import ToolRegistry

class LlmProcess(Process):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.caps = kwargs.get('caps', {})
        # These would be passed in by the kernel that spawns the process
        self.policy = {}
        self.keystore = {}
        self.host = self # Simplified for placeholder

        self.adapter = LlmAdapter(self.policy, self.keystore, self.caps)
        self.host_calls = HostCallsLLM(self.adapter)
        # self.window = self.host.alloc_buffer(480, 320) # Placeholder for UI
        self._render_ui("Ready. Ask me anything!")
        self._inflight_cancel = None
        self.tools = ToolRegistry(self.caps)

    def _redact(self, text: str) -> str:
        # Simplified keystore interaction
        redactions = [
            (self.keystore.get("api_key"), "<redacted>"),
            (self.keystore.get("secret_key"), "<redacted>")
        ]
        for secret, token in redactions:
            if secret:
                text = text.replace(secret, token)
        return text

    def _render_ui(self, status):
        # Placeholder for UI rendering
        print(f"[UI] Status: {status}")

    def _append_text(self, text, y):
        # Placeholder for UI rendering
        print(f"[UI] At y={y}: {text}")

    def get_font(self, font_name):
        # Placeholder for host services
        return None

    def on_prompt(self, text):
        # Reset cancel flag for new run
        if self._inflight_cancel:
            self._inflight_cancel()

        # Reset worker state
        worker = self.adapter.backends[self.adapter._choose_backend()]
        worker.reset()

        req = LlmRequest(
            model=self.caps.get("model", "pxos-mini-3b"),
            prompt=self._redact(text),
            stream=True,
            max_tokens=self.caps.get("max_tokens", 512),
            tools=self._get_tools_schema(),
            meta={"identity": f"pid:{self.pid}"}
        )

        def _cancel():
            worker.cancel()

        self._inflight_cancel = _cancel

        y = 24
        for chunk in self.host_calls.llm_infer(req):
            if chunk.tool_call:
                if self._handle_tool_call(chunk.tool_call) is False:
                    _cancel()
                    break

            if chunk.text:
                self._append_text(chunk.text, y)
                y += 12 # Simple y increment

            if chunk.done:
                break

        self._inflight_cancel = None

    def _get_tools_schema(self):
        if self.caps.get("tools"):
            return {
                "functions": [{
                    "name": "open_map",
                    "description": "Pan/zoom map",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "lon": {"type": "number"},
                            "zoom": {"type": "integer", "minimum": 0, "maximum": 22}
                        },
                        "required": ["lat", "lon"]
                    }
                }, {
                    "name": "bitpack_encode",
                    "description": "Emit BitPack image",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lang_id": {"type": "string", "maxLength": 8},
                            "payload": {"type": "string", "maxLength": 1000000}
                        },
                        "required": ["lang_id", "payload"]
                    }
                }]
            }
        return None

    def _handle_tool_call(self, ev):
        try:
            res = self.tools.call(ev.get("name"), ev.get("arguments", {}))
            self._append_text(f"\n[tool:{ev.get('name')}] {res}\n", 0)
            return True
        except Exception as e:
            self._append_text(f"\n[tool:error] {str(e)}\n", 0)
            return False

    def terminate(self):
        # Clean up resources on termination
        if self._inflight_cancel:
            self._inflight_cancel()

        worker = self.adapter.backends[self.adapter._choose_backend()]
        worker.cancel()
        worker.close()
        # super().terminate() # Assuming base class has terminate
        pass
