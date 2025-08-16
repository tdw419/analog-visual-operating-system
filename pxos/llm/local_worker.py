# pxos/llm/local_worker.py - Robust streaming with timeouts and resilient reads
import selectors, time, socket, json, errno
from .base_worker import BaseWorker, LlmLimits
from ..hostcalls_llm import LlmChunk

class LocalWorker(BaseWorker):
    def __init__(self, sock_path="/tmp/pxos-llm.sock"):
        super().__init__()
        self.sock_path = sock_path
        self.buffer = b""

    def stream(self, req, limits: LlmLimits):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(self.sock_path)
        s.setblocking(False)

        payload = {
            "prompt": req.prompt,
            "system": req.sys_prompt,
            "max_tokens": min(req.max_tokens, limits.max_tokens),
            "temperature": req.temperature,
        }
        s.sendall(json.dumps(payload).encode() + b"\n")

        sel = selectors.DefaultSelector()
        sel.register(s, selectors.EVENT_READ)
        last_token_ts = start_ts = time.monotonic()

        try:
            while not self._cancel.is_set():
                now = time.monotonic()
                if now - start_ts > limits.wall_timeout_s:
                    break
                if now - last_token_ts > limits.idle_timeout_s:
                    break

                events = sel.select(timeout=0.25)
                if not events:
                    continue

                for key, _ in events:
                    try:
                        chunk = key.fileobj.recv(8192)
                    except OSError as e:
                        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                            continue
                        yield LlmChunk(text="", done=True)
                        return

                    if not chunk:
                        yield LlmChunk(text="", done=True)
                        return

                    self.buffer += chunk
                    parts = self.buffer.split(b"\n")
                    lines, self.buffer = parts[:-1], parts[-1]

                    for line in lines:
                        if not line.strip():
                            continue

                        try:
                            ev = json.loads(line)
                        except json.JSONDecodeError:
                            self.buffer = line + b"\n"
                            continue

                        txt = ev.get("delta", "")
                        if txt:
                            last_token_ts = time.monotonic()

                        yield LlmChunk(
                            text=txt,
                            done=ev.get("done", False),
                            tool_call=ev.get("tool_call")
                        )

                        if ev.get("done", False):
                            return
        finally:
            try:
                s.close()
            except:
                pass
