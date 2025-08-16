# pxos/llm/adapter.py - Caps enforcement, backpressure, and model policies
from ..hostcalls_llm import LlmRequest, LlmChunk
from .ratelimit import RateLimiter
from .local_worker import LocalWorker
from .gateway_worker import GatewayWorker
from .base_worker import LlmLimits
from fnmatch import fnmatch

class LlmAdapter:
    def __init__(self, policy, keystore, caps):
        self.policy = policy
        self.keystore = keystore
        self.caps = dict(caps)  # immutable copy
        self.backends = {}

        # Instantiate gateway worker if allowed by policy
        if self.caps.get("net") and policy.get("trust_verdict") == "trusted":
            gateway_config_name = policy.get("llm_gateway")
            if gateway_config_name:
                # In a real app, this would fetch the full config dict
                # For now, we'll use a placeholder
                gateway_config = {
                    "url": "https://example.com/llm",
                    "headers": {"Authorization": f"Bearer {self.keystore.get('api_key')}"},
                    "timeout": 30
                }
                self.backends["gateway"] = GatewayWorker(gateway_config)

        # Always have a local fallback
        self.backends["local"] = LocalWorker()

        self.rate_limiter = RateLimiter(
            max_prompts_per_min=policy.get("max_prompts_per_min", 60),
            max_tokens_per_min=policy.get("max_tokens_per_min", 5000)
        )

    def _choose_backend(self):
        # Prefer gateway if it was successfully initialized
        if "gateway" in self.backends:
            return "gateway"
        return "local"

    def _model_allowed(self, model: str) -> bool:
        # normalize to avoid policy bypass via whitespace/case
        model = (model or "").strip().lower()
        allow = self.policy.get("llm_models_allow", ["pxos-*"])
        deny  = self.policy.get("llm_models_deny", [])
        if any(fnmatch(model, pat) for pat in deny):
            return False
        return any(fnmatch(model, pat) for pat in allow)

    def infer(self, req: LlmRequest):
        # Perform checks that return immediately
        if not self.rate_limiter.allow_request(req):
            return iter([LlmChunk(text="[rate limited]", done=True)])

        if not self._model_allowed(req.model):
            return iter([LlmChunk(text="[blocked: model not allowed]", done=True)])

        # If checks pass, delegate to the generator method
        return self._stream_infer(req)

    def _stream_infer(self, req: LlmRequest):
        # This is a generator method that handles the actual streaming
        max_tokens = min(req.max_tokens, int(self.caps.get("max_tokens", 512)))
        limits = LlmLimits(max_tokens=max_tokens)

        be = self.backends[self._choose_backend()]
        emitted = 0

        for chunk in be.stream(req, limits):
            if chunk.text:
                # Approximate token counting
                tokenizer = self.policy.get("tokenizer", lambda s: s.split())
                emitted += len(tokenizer(chunk.text))
                if emitted >= max_tokens:
                    yield LlmChunk(text="", done=True)
                    return

            yield chunk
