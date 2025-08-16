# pxos/llm/ratelimit.py - Thread-safe rate limiter
import time, threading
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class _Bucket:
    tokens: float
    last_refill: float

class RateLimiter:
    """
    Per-identity leaky bucket for prompts & tokens.
    Identity is taken from req.meta['identity'] (else 'global').
    """
    def __init__(self, max_prompts_per_min: int, max_tokens_per_min: int):
        self.max_prompts = float(max_prompts_per_min)
        self.max_tokens = float(max_tokens_per_min)
        self.prompts_rate = self.max_prompts / 60.0
        self.tokens_rate  = self.max_tokens  / 60.0
        self._prompts = defaultdict(lambda: _Bucket(tokens=self.max_prompts, last_refill=time.monotonic()))
        self._tokens  = defaultdict(lambda: _Bucket(tokens=self.max_tokens,  last_refill=time.monotonic()))
        self._lock = threading.Lock()

    def _refill(self, bucket: _Bucket, rate: float, capacity: float, now: float):
        elapsed = now - bucket.last_refill
        if elapsed > 0:
            bucket.tokens = min(capacity, bucket.tokens + rate * elapsed)
            bucket.last_refill = now

    def allow_request(self, req) -> bool:
        """
        Charges: 1 prompt + a conservative token budget (requested max_tokens).
        You can refine later by calling update_tokens() during streaming.
        """
        ident = (getattr(req, "meta", None) or {}).get("identity", "global")
        tokens_cost = float(getattr(req, "max_tokens", 0) or 0)
        now = time.monotonic()

        with self._lock:
            pb = self._prompts[ident]; self._refill(pb, self.prompts_rate, self.max_prompts, now)
            tb = self._tokens[ident];  self._refill(tb, self.tokens_rate,  self.max_tokens,  now)

            if pb.tokens < 1.0 or tb.tokens < tokens_cost:
                return False

            pb.tokens -= 1.0
            tb.tokens -= tokens_cost
            return True

    def update_tokens(self, ident: str, used_tokens: int):
        """Optional: call during streaming to decrement actual usage."""
        now = time.monotonic()
        with self._lock:
            tb = self._tokens[ident]; self._refill(tb, self.tokens_rate, self.max_tokens, now)
            tb.tokens = max(0.0, tb.tokens - float(used_tokens))
