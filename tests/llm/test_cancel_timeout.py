import types
from pxos.llm.base_worker import BaseWorker, LlmLimits
from pxos.hostcalls_llm import LlmRequest, LlmChunk

class SlowWorker(BaseWorker):
    def stream(self, req, limits):
        import time
        start = time.monotonic()
        while time.monotonic() - start < limits.idle_timeout_s + 1:
            if self._cancel.is_set():
                break
            time.sleep(0.1)
        yield LlmChunk(text="", done=True)

def test_idle_timeout():
    w = SlowWorker()
    req = LlmRequest(model="pxos-mini-3b", prompt="hi", max_tokens=8)
    lim = LlmLimits(max_tokens=8, idle_timeout_s=0.2, wall_timeout_s=5.0)
    chunks = list(w.stream(req, lim))
    assert chunks[-1].done is True

def test_cancel():
    w = SlowWorker()
    req = LlmRequest(model="pxos-mini-3b", prompt="hi", max_tokens=8)
    lim = LlmLimits(max_tokens=8, idle_timeout_s=10.0, wall_timeout_s=10.0)
    import threading
    out = []
    def run():
        for c in w.stream(req, lim): out.append(c)
    t = threading.Thread(target=run); t.start()
    w.cancel(); t.join(timeout=2)
    assert out and out[-1].done is True
