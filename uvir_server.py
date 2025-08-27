"""
UVIR 1.0 Server - Universal Visual Intermediate Representation
FastAPI backend for streaming visual operations from LLMs
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import json
import math
import uuid
import asyncio
import threading
import time
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

# Hardware integration
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not installed. Hardware commands will be simulated.")

# JSON repair utility
try:
    from json_repair import repair_json
except ImportError:
    # Fallback function if json_repair is not available
    def repair_json(text):
        return text

app = FastAPI(title="UVIR 1.0 Server", version="1.0.0")

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MODEL_PATH = os.environ.get("MODEL_PATH", "")
USE_MOCK = os.environ.get("USE_MOCK", "false").lower() == "true"
SERIAL_PORT = os.environ.get("SERIAL_PORT", "/dev/ttyUSB0")  # or COM3 on Windows

# LLM setup (if available)
llm = None
llm_lock = threading.Lock()

# Serial connection setup
serial_conn = None
if SERIAL_AVAILABLE:
    try:
        serial_conn = serial.Serial(SERIAL_PORT, 9600, timeout=1)
        print(f"✓ Connected to serial port: {SERIAL_PORT}")
    except Exception as e:
        print(f"Warning: Could not connect to serial port {SERIAL_PORT}: {e}")
        print("Hardware commands will be simulated.")

if not USE_MOCK and MODEL_PATH and os.path.exists(MODEL_PATH):
    try:
        from llama_cpp import Llama
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=8192,
            n_gpu_layers=-1,
            verbose=False
        )
        print(f"✓ Loaded model: {MODEL_PATH}")
    except ImportError:
        print("Warning: llama-cpp-python not installed. Using mock mode.")
        USE_MOCK = True
    except Exception as e:
        print(f"Warning: Could not load model: {e}. Using mock mode.")
        USE_MOCK = True
else:
    print("Using mock mode (set MODEL_PATH env var for real LLM)")
    USE_MOCK = True

# Active runs tracking
active_runs = {}
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# UVIR System Prompts
SYSTEM_IR = """You are a UVIR (Universal Visual Intermediate Representation) generator.
Generate visual operations as JSON arrays. Available operations:
- TICK: {"op": "TICK", "t": number} - temporal marker
- TEXT: {"op": "TEXT", "x": number, "y": number, "text": string, "color": "#RRGGBB", "size": number}
- BAR: {"op": "BAR", "x": number, "y": number, "len": number, "label": string, "value": 0-1, "color": "#RRGGBB"}
- RECT: {"op": "RECT", "x": number, "y": number, "w": number, "h": number, "color": "#RRGGBB", "fill": boolean}
- LINK: {"op": "LINK", "x1": number, "y1": number, "x2": number, "y2": number, "color": "#RRGGBB", "arrow": boolean}

For hardware control (e.g., 'set LED'), emit a tool_call: {"type": "tool_call", "name": "serial_pwm", "args": {"pin": int, "value": int}}.

Return ONLY valid JSON arrays or single tool_call objects. No prose, no code fences. Max 12 operations per response.
Coordinates: 0-1000 range. Example:
[{"op": "TEXT", "x": 50, "y": 100, "text": "Hello UVIR", "color": "#00FF00"}]"""

# Pydantic Models
class StreamRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    want_ir: bool = True
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(512, ge=1, le=2048)

class SerialPWMArgs(BaseModel):
    pin: int = Field(..., ge=0, le=255)
    value: int = Field(..., ge=0, le=255)

# Tool registry
TOOL_REGISTRY = {
    "serial_pwm": {
        "description": "Sends a PWM signal to a specified pin on a serial device.",
        "schema": SerialPWMArgs
    }
}

# Logging functions
def log_event(run_id: str, event: Dict[str, Any]):
    """Log event to NDJSON file for replay"""
    log_file = logs_dir / f"{run_id}.ndjson"
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            # Add timestamp for replay timing
            event_with_timestamp = {
                **event,
                "timestamp": time.time()
            }
            f.write(json.dumps(event_with_timestamp) + '\n')
            f.flush()
    except Exception as e:
        print(f"Warning: Failed to log event: {e}")

def get_log_files() -> List[str]:
    """Get list of available log files"""
    try:
        return [f.stem for f in logs_dir.glob("*.ndjson")]
    except Exception:
        return []
def entropy(top_probs: List[tuple]) -> float:
    """Calculate entropy from top probability list"""
    if not top_probs:
        return 0.0
    return -sum(p * math.log(max(p, 1e-9)) for _, p in top_probs)

def to_ir_step(step_idx: int, token: str, top_probs: List[tuple]) -> List[Dict]:
    """Convert token to visual IR operations"""
    p0 = top_probs[0][1] if top_probs else 0.0
    e = entropy(top_probs) if top_probs else 0.0
    y = 20 + (step_idx % 24) * 12
    
    return [
        {"op": "TICK", "t": step_idx},
        {"op": "TEXT", "x": 12, "y": y, "text": f"#{step_idx} '{token}' p0={p0:.2f} H={e:.2f}", "color": "#00FF00"},
        {"op": "BAR", "x": 10, "y": y + 8, "len": int(160 * p0), "label": token, "value": p0, "color": "#00AA00"},
    ]

def validate_uvir_ops(ops: List[Dict]) -> List[Dict]:
    """Validate and sanitize UVIR operations"""
    allowed_ops = {"TICK", "TEXT", "BAR", "RECT", "LINK"}
    validated = []
    
    for op in ops:
        if not isinstance(op, dict) or "op" not in op:
            continue
        if op["op"] not in allowed_ops:
            continue
        
        # Sanitize based on operation type
        clean_op = {"op": op["op"]}
        
        if op["op"] == "TICK":
            clean_op["t"] = max(0, min(10000, op.get("t", 0)))
        elif op["op"] == "TEXT":
            clean_op.update({
                "x": max(-1000, min(2000, op.get("x", 0))),
                "y": max(-1000, min(2000, op.get("y", 0))),
                "text": str(op.get("text", ""))[:256],
                "color": op.get("color", "#00FF00") if isinstance(op.get("color"), str) else "#00FF00",
                "size": max(8, min(48, op.get("size", 12)))
            })
        elif op["op"] == "BAR":
            clean_op.update({
                "x": max(-1000, min(2000, op.get("x", 0))),
                "y": max(-1000, min(2000, op.get("y", 0))),
                "len": max(0, min(1000, op.get("len", 0))),
                "label": str(op.get("label", ""))[:64],
                "value": max(0.0, min(1.0, op.get("value", 0.0))),
                "color": op.get("color", "#00AA00") if isinstance(op.get("color"), str) else "#00AA00"
            })
        elif op["op"] == "RECT":
            clean_op.update({
                "x": max(-1000, min(2000, op.get("x", 0))),
                "y": max(-1000, min(2000, op.get("y", 0))),
                "w": max(0, min(1000, op.get("w", 0))),
                "h": max(0, min(1000, op.get("h", 0))),
                "color": op.get("color", "#00FF00") if isinstance(op.get("color"), str) else "#00FF00",
                "fill": bool(op.get("fill", False))
            })
        elif op["op"] == "LINK":
            clean_op.update({
                "x1": max(-1000, min(2000, op.get("x1", 0))),
                "y1": max(-1000, min(2000, op.get("y1", 0))),
                "x2": max(-1000, min(2000, op.get("x2", 0))),
                "y2": max(-1000, min(2000, op.get("y2", 0))),
                "color": op.get("color", "#00FFFF") if isinstance(op.get("color"), str) else "#00FFFF",
                "arrow": bool(op.get("arrow", False))
            })
        
        validated.append(clean_op)
    
    return validated[:12]  # Limit to 12 operations

async def mock_generation(prompt: str, run_id: str):
    """Mock LLM generation for testing"""
    mock_tokens = ["Visualizing", " your", " request", "...", " Creating", " flowchart", " with", " UVIR", " operations"]
    
    for i, token in enumerate(mock_tokens):
        # Mock token event
        yield {
            "type": "token",
            "run_id": run_id,
            "step": i,
            "text": token
        }
        
        # Mock IR event
        yield {
            "type": "ir",
            "run_id": run_id,
            "step": i,
            "ops": to_ir_step(i, token, [(token, 0.8), ("alt", 0.1), ("other", 0.1)])
        }
        
        await asyncio.sleep(0.2)  # Simulate processing time
    
    # Mock summary
    mock_summary = [
        {"op": "TEXT", "x": 50, "y": 50, "text": f"UVIR Demo: {prompt[:30]}...", "color": "#FFFF00", "size": 16},
        {"op": "RECT", "x": 100, "y": 100, "w": 200, "h": 80, "color": "#00FFFF", "fill": False},
        {"op": "TEXT", "x": 120, "y": 130, "text": "Process Step", "color": "#FFFFFF"},
        {"op": "LINK", "x1": 200, "y1": 180, "x2": 200, "y2": 220, "arrow": True, "color": "#00FFFF"},
        {"op": "BAR", "x": 400, "y": 200, "len": 150, "label": "Progress", "value": 0.75, "color": "#00AA00"}
    ]
    
    yield {
        "type": "ir_summary",
        "run_id": run_id,
        "ops": validate_uvir_ops(mock_summary)
    }
    
    yield {
        "type": "done",
        "run_id": run_id,
        "usage": {"tokens_in": len(prompt.split()), "tokens_out": len(mock_tokens)}
    }

# API Endpoints

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "model": MODEL_PATH if MODEL_PATH else "mock",
        "mock_mode": USE_MOCK,
        "active_runs": len(active_runs),
        "serial_connected": serial_conn is not None
    }

@app.post("/stream")
async def stream_uvir(request: StreamRequest):
    """Stream UVIR events from LLM"""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    active_runs[run_id] = True
    
    # Log the initial request
    log_event(run_id, {
        "type": "request",
        "run_id": run_id,
        "prompt": request.prompt,
        "parameters": {
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "want_ir": request.want_ir
        }
    })
    
    async def generate():
        try:
            # Check for hardware-related prompts
            hardware_match = re.search(r"set\s+led\s+.*?\bpin\s+(\d+)\s+.*?\bvalue\s+(\d+)", request.prompt.lower())
            if hardware_match:
                pin, value = int(hardware_match.group(1)), int(hardware_match.group(2))
                tool_call = {
                    "type": "tool_call",
                    "run_id": run_id,
                    "name": "serial_pwm",
                    "args": {"pin": pin, "value": value}
                }
                yield f"data: {json.dumps(tool_call)}\n\n"
                # Execute tool call
                result = await execute_tool(tool_call)
                yield f"data: {json.dumps(result)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'run_id': run_id, 'usage': {'tokens_in': len(request.prompt.split()), 'tokens_out': 0}})}\n\n"
                return

            if USE_MOCK:
                # Use mock generation
                async for event in mock_generation(request.prompt, run_id):
                    if not active_runs.get(run_id, False):
                        break
                    log_event(run_id, event)  # Log all events
                    yield f"data: {json.dumps(event)}\n\n"
            else:
                # Real LLM generation
                with llm_lock:
                    chat = [
                        {"role": "system", "content": SYSTEM_IR},
                        {"role": "user", "content": request.prompt}
                    ]
                    
                    step = 0
                    for ev in llm.create_chat_completion(
                        messages=chat,
                        stream=True,
                        logprobs=5,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens
                    ):
                        if not active_runs.get(run_id, False):
                            break
                        
                        delta = ev["choices"][0].get("delta", {}).get("content") or ""
                        if not delta:
                            continue
                        
                        # Extract logprobs
                        k = []
                        lp = ev["choices"][0].get("logprobs", {}).get("top_logprobs", [])
                        if lp:
                            k = [(t, math.exp(v)) for t, v in lp[-1].items()]
                            k.sort(key=lambda x: x[1], reverse=True)
                        
                        # Token event
                        token_event = {
                            "type": "token",
                            "run_id": run_id,
                            "step": step,
                            "text": delta
                        }
                        yield f"data: {json.dumps(token_event)}\n\n"
                        
                        # IR event
                        if request.want_ir:
                            ops = to_ir_step(step, delta, k[:3])
                            ir_event = {
                                "type": "ir",
                                "run_id": run_id,
                                "step": step,
                                "ops": ops
                            }
                            yield f"data: {json.dumps(ir_event)}\n\n"
                        
                        step += 1
                        await asyncio.sleep(0.01)
                    
                    # Generate summary IR
                    if request.want_ir:
                        try:
                            ir_req = [
                                {"role": "system", "content": SYSTEM_IR},
                                {"role": "user", "content": f"Summarize '{request.prompt}' as up to 8 UVIR operations"}
                            ]
                            ir_resp = llm.create_chat_completion(messages=ir_req, temperature=0.2, max_tokens=256)
                            raw = ir_resp["choices"][0]["message"]["content"].strip()
                            cleaned = repair_json(raw)
                            ops = json.loads(cleaned)
                            validated_ops = validate_uvir_ops(ops)
                            
                            summary_event = {
                                "type": "ir_summary",
                                "run_id": run_id,
                                "ops": validated_ops
                            }
                            yield f"data: {json.dumps(summary_event)}\n\n"
                        except Exception as e:
                            print(f"IR summary error: {e}")
                    
                    # Done event
                    done_event = {
                        "type": "done",
                        "run_id": run_id,
                        "usage": {"tokens_in": len(request.prompt.split()), "tokens_out": step}
                    }
                    yield f"data: {json.dumps(done_event)}\n\n"
        
        finally:
            active_runs.pop(run_id, None)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/runs/{run_id}/abort")
async def abort_run(run_id: str):
    """Abort a running generation"""
    if run_id in active_runs:
        active_runs[run_id] = False
    return {"ok": True, "run_id": run_id}

@app.get("/logs")
async def list_logs():
    """Get list of available log files"""
    return {"logs": get_log_files()}

@app.post("/replay")
async def replay_session(request: Request):
    """Replay a logged session from NDJSON file"""
    data = await request.json()
    run_id = data.get("run_id")
    speed = data.get("speed", 1.0)  # Playback speed multiplier
    
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id required")
    
    log_file = logs_dir / f"{run_id}.ndjson"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    async def generate_replay():
        try:
            events = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
            
            if not events:
                return
            
            # Calculate timing for replay
            first_timestamp = events[0].get("timestamp", 0)
            
            for i, event in enumerate(events):
                # Remove timestamp from replay event
                replay_event = {k: v for k, v in event.items() if k != "timestamp"}
                
                # Calculate delay based on original timing
                if i > 0 and "timestamp" in event and "timestamp" in events[i-1]:
                    original_delay = event["timestamp"] - events[i-1]["timestamp"]
                    replay_delay = original_delay / speed
                    if replay_delay > 0:
                        await asyncio.sleep(min(replay_delay, 2.0))  # Cap delay at 2 seconds
                
                yield f"data: {json.dumps(replay_event)}\n\n"
                
        except Exception as e:
            error_event = {
                "type": "error",
                "error": f"Replay failed: {str(e)}"
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate_replay(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/tools/execute")
async def execute_tool(tool_call: Dict[str, Any]):
    """Execute a tool call"""
    tool_name = tool_call.get("name")
    args = tool_call.get("args", {})
    run_id = tool_call.get("run_id", "unknown")
    
    if tool_name not in TOOL_REGISTRY:
        return {
            "type": "tool_result",
            "run_id": run_id,
            "name": tool_name,
            "ok": False,
            "result": {"error": f"Tool '{tool_name}' not found."}
        }
    
    try:
        schema = TOOL_REGISTRY[tool_name]["schema"]
        validated_args = schema.parse_obj(args)
        
        if tool_name == "serial_pwm":
            if serial_conn:
                # Real hardware control
                serial_conn.write(f"PWM:{validated_args.pin}:{validated_args.value}\n".encode())
                response = serial_conn.readline().decode().strip()
                if response == "OK":
                    print(f"✓ Hardware PWM: Pin {validated_args.pin}, Value {validated_args.value}")
                    return {
                        "type": "tool_result",
                        "run_id": run_id,
                        "name": tool_name,
                        "ok": True,
                        "result": {"message": f"PWM set on pin {validated_args.pin} to {validated_args.value}"}
                    }
                else:
                    return {
                        "type": "tool_result",
                        "run_id": run_id,
                        "name": tool_name,
                        "ok": False,
                        "result": {"error": f"Hardware error: {response}"}
                    }
            else:
                # Simulate PWM control
                print(f"Simulating serial PWM: Pin {validated_args.pin}, Value {validated_args.value}")
                return {
                    "type": "tool_result",
                    "run_id": run_id,
                    "name": tool_name,
                    "ok": True,
                    "result": {"message": f"Simulated PWM on pin {validated_args.pin} to {validated_args.value} (no hardware)"}
                }
    except Exception as e:
        return {
            "type": "tool_result",
            "run_id": run_id,
            "name": tool_name,
            "ok": False,
            "result": {"error": str(e)}
        }
    
    return {
        "type": "tool_result",
        "run_id": run_id,
        "name": tool_name,
        "ok": False,
        "result": {"error": "Tool not implemented"}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8844, reload=True)