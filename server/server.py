# server.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from llama_cpp import Llama
import os, json, math

MODEL_PATH = os.environ.get("MODEL_PATH", "models/llama-3-8b-instruct.Q4_K_M.gguf")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model once
llm = Llama(model_path=MODEL_PATH, n_ctx=8192, logits_all=False)

SYSTEM_IR = (
    "You are a visualization co-processor. "
    "When asked, you emit only a JSON array of draw ops using keys: op, TEXT, BAR, LINK, TICK, RECT. "
    "Strict JSON. Max ~12 ops."
)

def entropy(top):
    return -sum(p * math.log(max(p, 1e-9)) for _, p in top)

def to_ir_step(step_idx, token, top):
    p0 = top[0][1] if top else 0.0
    e = entropy(top) if top else 0.0
    y = 20 + (step_idx % 24) * 12  # wrap vertically
    return [
        {"op": "TICK", "t": step_idx},
        {"op": "TEXT", "x": 12, "y": y, "text": f"#{step_idx} '{token}' p0={p0:.2f} H={e:.2f}"},
        {"op": "BAR",  "x": 10, "y": y + 8, "len": int(160 * p0), "label": token},
    ]

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/stream")
def stream(prompt: str, want_ir: bool = True, topk: int = 5, temperature: float = 0.8, top_p: float = 0.95):
    def gen():
        chat = [
            {"role": "system", "content": "Stream tokens clearly."},
            {"role": "user", "content": prompt},
        ]
        step = 0

        # llama.cpp streaming chat completion
        for ev in llm.create_chat_completion(
            messages=chat, stream=True, temperature=temperature, top_p=top_p, logprobs=topk
        ):
            ch = ev["choices"][0]
            delta = ch.get("delta", {}).get("content") or ""
            if not delta:
                continue

            # Best-effort top-k from logprobs
            k = []
            lp = ch.get("logprobs")
            if lp and lp.get("top_logprobs"):
                top_list = lp["top_logprobs"][0]  # dict of {token: logprob}
                k = [(tok, math.exp(v)) for tok, v in top_list.items()]
                s = sum(p for _, p in k) or 1.0
                k = [(t, p / s) for t, p in k]
                k.sort(key=lambda x: x[1], reverse=True)

            yield f"data: {json.dumps({'type':'token','text': delta})}\n\n"

            if want_ir:
                ops = to_ir_step(step, delta, k[:3])
                yield f"data: {json.dumps({'type':'ir','ops': ops})}\n\n"
            step += 1

        # Optional compact summary IR composed by the model
        if want_ir:
            ir_req = [
                {"role": "system", "content": SYSTEM_IR},
                {"role": "user", "content": "Summarize the response as up to 12 draw ops."},
            ]
            ir_resp = llm.create_chat_completion(messages=ir_req)
            try:
                summary = ir_resp["choices"][0]["message"]["content"].strip()
                yield f"data: {json.dumps({'type':'ir_summary','ops': json.loads(summary)})}\n\n"
            except Exception:
                pass

        yield "data: {\"type\":\"done\"}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
