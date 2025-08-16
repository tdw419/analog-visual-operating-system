# pxos/llm/gateway_worker.py - HTTP/SSE client for remote LLM services
import requests
import json
from .base_worker import BaseWorker, LlmLimits
from ..hostcalls_llm import LlmRequest, LlmChunk

class GatewayWorker(BaseWorker):
    def __init__(self, config):
        """
        Initialize gateway worker with configuration
        :param config: Dictionary containing:
            - url: Gateway URL (with protocol)
            - headers: Authentication headers (like Bearer token)
            - timeout: Request timeout in seconds
        """
        super().__init__()
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.get('headers', {}))
        self.timeout = config.get('timeout', 30)

    def stream(self, req: LlmRequest, limits: LlmLimits):
        """
        Stream tokens from remote LLM service using Server-Sent Events (SSE)
        """
        # Prepare request parameters
        params = {
            "model": req.model,
            "prompt": req.prompt,
            "system": req.sys_prompt,
            "max_tokens": min(req.max_tokens, limits.max_tokens),
            "temperature": req.temperature,
            "stream": True
        }

        try:
            # Make streaming request
            response = self.session.post(
                self.config['url'],
                json=params,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Parse and yield SSE events
            for line in response.iter_lines(decode_unicode=True):
                if self._cancel.is_set():
                    break
                if not line or not line.startswith("data: "):
                    continue

                data = line[6:]  # Remove "data: " prefix

                if data == "[DONE]":
                    yield LlmChunk(text="", done=True)
                    return

                try:
                    event = json.loads(data)
                    yield LlmChunk(
                        text=event.get("delta", ""),
                        done=event.get("done", False),
                        tool_call=event.get("tool_call")
                    )
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue

        except requests.exceptions.RequestException as e:
            # Handle network errors gracefully
            yield LlmChunk(text=f"[gateway_error: {str(e)}]", done=True)
            return
