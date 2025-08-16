# pxos/hostcalls_llm.py - Final enhanced version
from dataclasses import dataclass
from typing import Iterable, Optional, Dict, Any
import json

@dataclass
class LlmRequest:
    model: str
    prompt: str
    sys_prompt: str = ""
    stream: bool = True
    max_tokens: int = 512
    temperature: float = 0.7
    tools: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

@dataclass
class LlmChunk:
    text: str
    done: bool = False
    tool_call: Optional[Dict[str, Any]] = None

class HostCallsLLM:
    def __init__(self, adapter):
        self.adapter = adapter

    def llm_infer(self, req: LlmRequest) -> Iterable[LlmChunk]:
        return self.adapter.infer(req)
