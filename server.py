# server.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import os, json, time, re, serial, logging, ndjson
from typing import Dict, List, Any, Optional
from enum import Enum
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvir-bridge")

app = FastAPI(title="UVIR 1.0 Bridge", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- Configuration ---
MODEL_PATH = os.getenv("MODEL_PATH") # Path to your GGUF model
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0") # Arduino serial port
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "true").lower() == "true"

# --- Pydantic Models (The UVIR Contract) ---
class UVIROp(BaseModel):
    op: str = Field(..., description="Operation type: TICK, TEXT, BAR, RECT, LINK")
    # TICK
    t: Optional[int] = Field(None, ge=0, le=10000)
    # TEXT, BAR, RECT, LINK
    x: Optional[int] = Field(None, ge=-1000, le=2000)
    y: Optional[int] = Field(None, ge=-1000, le=2000)
    # TEXT
    text: Optional[str] = Field(None, max_length=256)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    size: Optional[int] = Field(None, ge=8, le=48)
    # BAR
    len: Optional[int] = Field(None, ge=0, le=1000)
    label: Optional[str] = Field(None, max_length=64)
    value: Optional[float] = Field(None, ge=0.0, le=1.0)
    # RECT
    w: Optional[int] = Field(None, ge=0, le=1000)
    h: Optional[int] = Field(None, ge=0, le=1000)
    fill: Optional[bool] = None
    # LINK
    x1: Optional[int] = Field(None, ge=-1000, le=2000)
    y1: Optional[int] = Field(None, ge=-1000, le=2000)
    x2: Optional[int] = Field(None, ge=-1000, le=2000)
    y2: Optional[int] = Field(None, ge=-1000, le=2000)
    arrow: Optional[bool] = None

class StreamRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    want_ir: bool = True

class SerialPWMArgs(BaseModel):
    pin: int = Field(..., ge=0, le=13)
    value: int = Field(..., ge=0, le=255)

# --- Tool Registry ---
class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.serial_conn = None
        self._init_serial()

    def _init_serial(self):
        try:
            self.serial_conn = serial.Serial(SERIAL_PORT, 9600, timeout=1)
            logger.info(f"Connected to hardware at {SERIAL_PORT}")
        except Exception as e:
            logger.warning(f"Could not connect to hardware. Simulating. Error: {e}")
            self.serial_conn = None

    def register(self, name, schema, func):
        self.tools[name] = {"schema": schema, "func": func}

    async def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.tools:
            return {"ok": False, "error": f"Tool '{name}' not found."}
        try:
            schema = self.tools[name]["schema"]
            validated_args = schema(**args) # Validate and clamp
            result = await self.tools[name]["func"](validated_args)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

# --- Tool Implementation: serial_pwm ---
tool_registry = ToolRegistry()

async def serial_pwm_execute(args: SerialPWMArgs):
    cmd = f"PWM:{args.pin}:{args.value}\n".encode()
    if tool_registry.serial_conn:
        tool_registry.serial_conn.write(cmd)
        response = tool_registry.serial_conn.readline().decode().strip()
        return {"message": f"Set pin {args.pin} to {args.value}", "response": response}
    else:
        # Simulation mode
        return {"message": f"SIMULATED: Set pin {args.pin} to {args.value}", "simulated": True}

tool_registry.register("serial_pwm", SerialPWMArgs, serial_pwm_execute)

# --- LLM Mock (For Initial Testing) ---
async def mock_llm_generation(prompt: str, run_id: str):
    """A mock LLM that generates a simple UVIR stream for testing."""
    logger.info(f"MOCK LLM generating for prompt: {prompt}")

    # Check for hardware command
    hw_match = re.search(r"set\s+led.*pin\s+(\d+).*value\s+(\d+)", prompt.lower())
    if hw_match:
        pin, value = int(hw_match.group(1)), int(hw_match.group(2))
        yield json.dumps({"type": "tool_call", "run_id": run_id, "name": "serial_pwm", "args": {"pin": pin, "value": value}})
        result = await tool_registry.execute("serial_pwm", {"pin": pin, "value": value})
        yield json.dumps({"type": "tool_result", "run_id": run_id, "name": "serial_pwm", "ok": result["ok"], "result": result["result"]})
        yield json.dumps({"type": "done", "run_id": run_id})
        return

    # Default: Generate a visual response
    mock_tokens = ["Hello", " ", "UVIR", "!", " ", "This", " ", "is", " ", "live."]
    mock_ops = [
        [{"op": "TEXT", "x": 50, "y": 50, "text": "Welcome", "color": "#00FF00", "size": 24}],
        [{"op": "RECT", "x": 45, "y": 45, "w": 200, "h": 40, "fill": False, "color": "#00AA00"}],
        [{"op": "BAR", "x": 50, "y": 100, "len": 150, "label": "Progress", "value": 0.5, "color": "#0000FF"}]
    ]

    for i, token in enumerate(mock_tokens):
        yield json.dumps({"type": "token", "run_id": run_id, "text": token})
        if i % 2 == 0: # Interleave IR ops
            yield json.dumps({"type": "ir", "run_id": run_id, "ops": mock_ops[i % len(mock_ops)]})
        time.sleep(0.1)
    yield json.dumps({"type": "done", "run_id": run_id})

# --- Core API Endpoints ---
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "model_loaded": not USE_MOCK_LLM,
        "hardware_connected": tool_registry.serial_conn is not None
    }

@app.post("/stream")
async def stream_response(request: StreamRequest):
    """The main endpoint: streams tokens, UVIR ops, and tool calls/results."""
    run_id = f"run_{int(time.time())}_{os.urandom(4).hex()}"
    log_file = Path(f"logs/{run_id}.ndjson")
    log_file.parent.mkdir(exist_ok=True)

    async def event_generator():
        logger.info(f"Starting stream for run_id: {run_id}")
        events = []

        try:
            # Get the event stream (from mock or real LLM)
            if USE_MOCK_LLM:
                event_stream = mock_llm_generation(request.prompt, run_id)
            else:
                # TODO: Integrate llama.cpp here
                event_stream = mock_llm_generation(request.prompt, run_id)

            # Stream events and log them
            async for event in event_stream:
                event_data = event
                events.append(event_data)
                with open(log_file, 'a') as f:
                    f.write(event_data + '\n')
                yield f"data: {event_data}\n\n"

        except Exception as e:
            error_event = json.dumps({"type": "error", "run_id": run_id, "error": str(e)})
            yield f"data: {error_event}\n\n"
        logger.info(f"Finished stream for run_id: {run_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/tools/execute")
async def execute_tool(payload: Dict[str, Any]):
    """Endpoint for direct tool execution (e.g., from the frontend)."""
    name = payload.get("name")
    args = payload.get("args", {})
    run_id = payload.get("run_id", "manual")
    result = await tool_registry.execute(name, args)
    return {"type": "tool_result", "run_id": run_id, "name": name, "ok": result["ok"], "result": result["result"]}

@app.get("/replay/{run_id}")
async def replay_run(run_id: str):
    """Replays a logged session."""
    log_file = Path(f"logs/{run_id}.ndjson")
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    async def replay_generator():
        with open(log_file, 'r') as f:
            for line in f:
                yield f"data: {line.strip()}\n\n"
                time.sleep(0.05) # Simulate real-time playback

    return StreamingResponse(replay_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8844, reload=True)
