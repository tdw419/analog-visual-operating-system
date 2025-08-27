"""
Infinite UVIR Server - HTTP/WebSocket API for Infinite Visual Computer
Integrates the infinite visual computer with UVIR visualization system
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from infinite_visual_computer import InfiniteVisualComputer, ChunkCoordinate, PixelCoordinate

app = FastAPI(title="Infinite UVIR Server", description="Universal Visual IR for Infinite Computational Space")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global infinite visual computer instance
infinite_computer = InfiniteVisualComputer(chunk_size=64, max_loaded_chunks=100)

# UVIR Operation Extensions for Infinite Space
@dataclass
class InfiniteUVIROperation:
    """Extended UVIR operation with infinite coordinate support"""
    op: str
    world_x: Optional[int] = None
    world_y: Optional[int] = None
    chunk_x: Optional[int] = None
    chunk_y: Optional[int] = None
    local_x: Optional[int] = None
    local_y: Optional[int] = None
    viewport_x: Optional[int] = None  # For relative positioning within viewport
    viewport_y: Optional[int] = None
    # Standard UVIR fields
    x: Optional[int] = None
    y: Optional[int] = None
    w: Optional[int] = None
    h: Optional[int] = None
    color: Optional[str] = None
    text: Optional[str] = None
    size: Optional[int] = None
    fill: Optional[bool] = None
    # Extended fields
    data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None
    frame: Optional[int] = None
    layer: Optional[str] = None

class InfiniteUVIRRenderer:
    """Renders UVIR operations for infinite visual computer"""
    
    def __init__(self, computer: InfiniteVisualComputer):
        self.computer = computer
        self.viewport = {"world_x": 0, "world_y": 0, "width": 1200, "height": 800, "zoom": 1.0}
        self.active_connections: Set[WebSocket] = set()
    
    def set_viewport(self, world_x: int, world_y: int, width: int, height: int, zoom: float = 1.0):
        """Set the current viewport for rendering"""
        self.viewport = {
            "world_x": world_x,
            "world_y": world_y, 
            "width": width,
            "height": height,
            "zoom": zoom
        }
    
    def world_to_viewport(self, world_x: int, world_y: int) -> Tuple[int, int]:
        """Convert world coordinates to viewport coordinates"""
        rel_x = (world_x - self.viewport["world_x"]) * self.viewport["zoom"]
        rel_y = (world_y - self.viewport["world_y"]) * self.viewport["zoom"]
        viewport_x = rel_x + self.viewport["width"] // 2
        viewport_y = rel_y + self.viewport["height"] // 2
        return int(viewport_x), int(viewport_y)
    
    def render_operations(self, operations: List[InfiniteUVIROperation]) -> List[Dict[str, Any]]:
        """Render infinite UVIR operations to standard UVIR format"""
        rendered_ops = []
        
        for op in operations:
            # Convert to world coordinates if needed
            if op.world_x is not None and op.world_y is not None:
                viewport_x, viewport_y = self.world_to_viewport(op.world_x, op.world_y)
            elif op.chunk_x is not None and op.chunk_y is not None and op.local_x is not None and op.local_y is not None:
                world_x = op.chunk_x * self.computer.chunk_size + op.local_x
                world_y = op.chunk_y * self.computer.chunk_size + op.local_y
                viewport_x, viewport_y = self.world_to_viewport(world_x, world_y)
            else:
                viewport_x, viewport_y = op.viewport_x or op.x or 0, op.viewport_y or op.y or 0
            
            # Skip if outside viewport (with some margin)
            margin = 100
            if (viewport_x < -margin or viewport_x > self.viewport["width"] + margin or
                viewport_y < -margin or viewport_y > self.viewport["height"] + margin):
                continue
            
            # Create standard UVIR operation
            rendered_op = {
                "op": op.op,
                "x": viewport_x,
                "y": viewport_y
            }
            
            # Add optional fields with zoom scaling
            if op.w is not None:
                rendered_op["w"] = max(1, int(op.w * self.viewport["zoom"]))
            if op.h is not None:
                rendered_op["h"] = max(1, int(op.h * self.viewport["zoom"]))
            if op.color is not None:
                rendered_op["color"] = op.color
            if op.text is not None:
                rendered_op["text"] = op.text
            if op.size is not None:
                rendered_op["size"] = max(6, int(op.size * self.viewport["zoom"]))
            if op.fill is not None:
                rendered_op["fill"] = op.fill
                
            rendered_ops.append(rendered_op)
        
        return rendered_ops
    
    def get_viewport_operations(self) -> List[Dict[str, Any]]:
        """Get UVIR operations for current viewport"""
        operations = []
        
        # Calculate visible chunk range
        chunk_size = self.computer.chunk_size
        world_left = self.viewport["world_x"] - self.viewport["width"] // (2 * self.viewport["zoom"])
        world_right = self.viewport["world_x"] + self.viewport["width"] // (2 * self.viewport["zoom"])
        world_top = self.viewport["world_y"] - self.viewport["height"] // (2 * self.viewport["zoom"])
        world_bottom = self.viewport["world_y"] + self.viewport["height"] // (2 * self.viewport["zoom"])
        
        chunk_left = int(world_left // chunk_size) - 1
        chunk_right = int(world_right // chunk_size) + 1
        chunk_top = int(world_top // chunk_size) - 1
        chunk_bottom = int(world_bottom // chunk_size) + 1
        
        # Draw coordinate system
        operations.extend([
            InfiniteUVIROperation(
                op="RECT",
                world_x=self.viewport["world_x"] - 500,
                world_y=self.viewport["world_y"],
                w=1000,
                h=1,
                color="#FF0000",
                fill=True
            ),
            InfiniteUVIROperation(
                op="RECT", 
                world_x=self.viewport["world_x"],
                world_y=self.viewport["world_y"] - 500,
                w=1,
                h=1000,
                color="#FF0000",
                fill=True
            )
        ])
        
        # Draw chunk boundaries and contents
        for chunk_x in range(chunk_left, chunk_right + 1):
            for chunk_y in range(chunk_top, chunk_bottom + 1):
                chunk_coord = ChunkCoordinate(chunk_x, chunk_y)
                
                # Draw chunk boundary
                world_x = chunk_x * chunk_size
                world_y = chunk_y * chunk_size
                
                operations.append(InfiniteUVIROperation(
                    op="RECT",
                    world_x=world_x,
                    world_y=world_y,
                    w=chunk_size,
                    h=chunk_size,
                    color="#333333",
                    fill=False
                ))
                
                # Add chunk info
                operations.append(InfiniteUVIROperation(
                    op="TEXT",
                    world_x=world_x + chunk_size // 2,
                    world_y=world_y + chunk_size // 2,
                    text=f"({chunk_x},{chunk_y})",
                    color="#666666",
                    size=8
                ))
                
                # If chunk is loaded, draw its contents
                if chunk_coord in self.computer.loaded_chunks:
                    chunk = self.computer.loaded_chunks[chunk_coord]
                    
                    # Draw chunk state indicator
                    state_colors = {
                        "foundation": "#FF0000",
                        "computing": "#00FF00", 
                        "evolving": "#FF8800",
                        "idle": "#888888"
                    }
                    state_color = state_colors.get(chunk.compute_state.value, "#FFFFFF")
                    
                    operations.append(InfiniteUVIROperation(
                        op="RECT",
                        world_x=world_x + 2,
                        world_y=world_y + 2,
                        w=6,
                        h=6,
                        color=state_color,
                        fill=True
                    ))
                    
                    # Draw individual pixels if zoomed in enough
                    if self.viewport["zoom"] > 1.0:
                        pixel_step = max(1, int(8 / self.viewport["zoom"]))  # Sample pixels
                        for local_y in range(0, chunk.size, pixel_step):
                            for local_x in range(0, chunk.size, pixel_step):
                                pixel = chunk.get_pixel(local_x, local_y)
                                if sum(pixel[:3]) > 0:  # Non-black pixel
                                    operations.append(InfiniteUVIROperation(
                                        op="RECT",
                                        world_x=world_x + local_x,
                                        world_y=world_y + local_y,
                                        w=pixel_step,
                                        h=pixel_step,
                                        color=f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}",
                                        fill=True
                                    ))
        
        return self.render_operations(operations)

# Global renderer
renderer = InfiniteUVIRRenderer(infinite_computer)

# WebSocket connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "viewport_change":
                renderer.set_viewport(
                    message["world_x"],
                    message["world_y"],
                    message["width"],
                    message["height"],
                    message.get("zoom", 1.0)
                )
                
                # Send updated operations
                ops = renderer.get_viewport_operations()
                response = {
                    "type": "ir",
                    "ops": ops,
                    "stats": infinite_computer.get_statistics()
                }
                await websocket.send_text(json.dumps(response))
                
            elif message.get("type") == "pixel_set":
                # Set pixel at clicked location
                world_x = message["world_x"]
                world_y = message["world_y"]
                color_hex = message.get("color", "#00FF00")
                
                # Parse hex color
                if color_hex.startswith("#"):
                    r = int(color_hex[1:3], 16)
                    g = int(color_hex[3:5], 16)
                    b = int(color_hex[5:7], 16)
                    a = 255
                else:
                    r, g, b, a = 255, 255, 255, 255
                
                infinite_computer.set_world_pixel(world_x, world_y, (r, g, b, a))
                
                # Broadcast update
                ops = renderer.get_viewport_operations()
                await manager.broadcast(json.dumps({"type": "ir", "ops": ops}))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Pydantic models for API
class PixelRequest(BaseModel):
    world_x: int
    world_y: int
    color: str = "#00FF00"

class MemoryRequest(BaseModel):
    world_x: int
    world_y: int
    data: Any
    memory_type: str = "spatial"

class FilesystemRequest(BaseModel):
    world_x: int
    world_y: int
    frame: int
    data: Any

class DatabaseRequest(BaseModel):
    world_x: int
    world_y: int
    table: str
    entity_id: str
    data: Dict[str, Any]

class ViewportRequest(BaseModel):
    world_x: int
    world_y: int
    width: int
    height: int
    zoom: float = 1.0

class RegionQueryRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    table: str
    frame: Optional[int] = None

# API Endpoints
@app.get("/")
async def get_root():
    return {"message": "Infinite Visual Computer UVIR Server", "version": "1.0.0"}

@app.post("/infinite/pixel")
async def set_infinite_pixel(request: PixelRequest):
    """Set pixel in infinite space"""
    # Parse color
    if request.color.startswith("#"):
        r = int(request.color[1:3], 16)
        g = int(request.color[3:5], 16)
        b = int(request.color[5:7], 16)
        a = 255
    else:
        r, g, b, a = 255, 255, 255, 255
    
    infinite_computer.set_world_pixel(request.world_x, request.world_y, (r, g, b, a))
    
    # Broadcast update to all connected clients
    ops = renderer.get_viewport_operations()
    await manager.broadcast(json.dumps({"type": "ir", "ops": ops}))
    
    return {"success": True, "world_x": request.world_x, "world_y": request.world_y}

@app.get("/infinite/pixel")
async def get_infinite_pixel(world_x: int, world_y: int):
    """Get pixel from infinite space"""
    pixel = infinite_computer.get_world_pixel(world_x, world_y)
    return {
        "world_x": world_x,
        "world_y": world_y,
        "color": f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}",
        "rgba": pixel
    }

@app.post("/infinite/memory/write")
async def write_infinite_memory(request: MemoryRequest):
    """Write to visual memory in infinite space"""
    infinite_computer.visual_memory_write(
        request.world_x, request.world_y, request.data, request.memory_type
    )
    
    return {"success": True, "memory_type": request.memory_type}

@app.get("/infinite/memory/read")
async def read_infinite_memory(world_x: int, world_y: int, memory_type: str = "spatial"):
    """Read from visual memory in infinite space"""
    data = infinite_computer.visual_memory_read(world_x, world_y, memory_type)
    return {"data": data, "world_x": world_x, "world_y": world_y, "memory_type": memory_type}

@app.post("/infinite/filesystem/write")
async def write_infinite_filesystem(request: FilesystemRequest):
    """Write to frame filesystem in infinite space"""
    infinite_computer.frame_filesystem_write(
        request.world_x, request.world_y, request.frame, request.data
    )
    
    return {"success": True, "frame": request.frame}

@app.get("/infinite/filesystem/read")
async def read_infinite_filesystem(world_x: int, world_y: int, frame: int):
    """Read from frame filesystem in infinite space"""
    data = infinite_computer.frame_filesystem_read(world_x, world_y, frame)
    return {"data": data, "world_x": world_x, "world_y": world_y, "frame": frame}

@app.post("/infinite/database/insert")
async def insert_infinite_database(request: DatabaseRequest):
    """Insert into temporal database in infinite space"""
    infinite_computer.temporal_database_insert(
        request.world_x, request.world_y, request.table, request.entity_id, request.data
    )
    
    # Broadcast update
    ops = renderer.get_viewport_operations()
    await manager.broadcast(json.dumps({"type": "ir", "ops": ops}))
    
    return {"success": True, "table": request.table, "entity_id": request.entity_id}

@app.post("/infinite/database/query")
async def query_infinite_database(request: RegionQueryRequest):
    """Query temporal database in infinite space"""
    region = (request.x1, request.y1, request.x2, request.y2)
    results = infinite_computer.temporal_database_query(region, request.table, request.frame)
    
    return {"results": results, "count": len(results)}

@app.post("/infinite/compute/step")
async def compute_step():
    """Execute one computation step"""
    changed_chunks = infinite_computer.advance_frame()
    
    # Broadcast update to all connected clients
    ops = renderer.get_viewport_operations()
    stats = infinite_computer.get_statistics()
    
    await manager.broadcast(json.dumps({
        "type": "ir", 
        "ops": ops,
        "stats": stats,
        "changed_chunks": changed_chunks
    }))
    
    return {
        "success": True, 
        "frame": stats["current_frame"], 
        "changed_chunks": changed_chunks,
        "stats": stats
    }

@app.post("/infinite/viewport")
async def set_viewport(request: ViewportRequest):
    """Set rendering viewport"""
    renderer.set_viewport(
        request.world_x,
        request.world_y,
        request.width,
        request.height,
        request.zoom
    )
    
    ops = renderer.get_viewport_operations()
    return {"type": "ir", "ops": ops, "viewport": renderer.viewport}

@app.get("/infinite/stats")
async def get_infinite_stats():
    """Get infinite computer statistics"""
    return infinite_computer.get_statistics()

@app.post("/infinite/save")
async def save_infinite_state():
    """Save all chunks to persistent storage"""
    infinite_computer.save_all_chunks()
    stats = infinite_computer.get_statistics()
    return {"success": True, "chunks_saved": stats["chunks_saved"]}

@app.get("/infinite/region/chunks")
async def get_region_chunks(x1: int, y1: int, x2: int, y2: int):
    """Get chunk coordinates in world region"""
    chunks = infinite_computer.get_chunk_region(x1, y1, x2, y2)
    return {
        "chunks": [{"x": c.x, "y": c.y} for c in chunks],
        "count": len(chunks)
    }

# Streaming scenarios
@app.get("/infinite/scenario/cellular_life")
async def run_cellular_life_scenario():
    """Run Conway's Game of Life scenario across infinite space"""
    
    def scenario_generator():
        # Set up initial patterns across multiple chunks
        patterns = [
            # Glider at origin
            (0, 0, [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]),
            
            # Glider in distant chunk
            (500, 300, [(501, 300), (502, 301), (500, 302), (501, 302), (502, 302)]),
            
            # Oscillator (blinker)
            (-200, 100, [(-200, 100), (-200, 101), (-200, 102)]),
            
            # Block (stable)
            (100, -150, [(100, -150), (101, -150), (100, -149), (101, -149)]),
            
            # Lightweight spaceship
            (800, 800, [(800, 800), (803, 800), (799, 801), (799, 802), (799, 803), (800, 803), (801, 803), (802, 803), (803, 802)])
        ]
        
        # Initialize patterns
        for center_x, center_y, pattern in patterns:
            for x, y in pattern:
                infinite_computer.set_world_pixel(x, y, (255, 255, 255, 255))
        
        yield f"data: {json.dumps({'type': 'status', 'message': 'Initialized Conway Life patterns'})}\n\n"
        
        # Run simulation
        for step in range(100):
            changed_chunks = infinite_computer.advance_frame()
            stats = infinite_computer.get_statistics()
            
            ops = renderer.get_viewport_operations()
            
            yield f"data: {json.dumps({
                'type': 'ir',
                'ops': ops,
                'frame': stats['current_frame'],
                'step': step,
                'changed_chunks': changed_chunks,
                'stats': stats,
                'message': f'Life step {step}: {changed_chunks} chunks changed'
            })}\n\n"
            
            time.sleep(0.3)  # ~3 FPS
        
        yield f"data: {json.dumps({'type': 'done', 'message': 'Cellular life scenario complete'})}\n\n"
    
    return StreamingResponse(
        scenario_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/infinite/scenario/memory_test")
async def run_memory_test_scenario():
    """Test visual memory systems across infinite space"""
    
    def scenario_generator():
        yield f"data: {json.dumps({'type': 'status', 'message': 'Starting memory test scenario'})}\n\n"
        
        # Test spatial memory
        for i in range(20):
            x, y = i * 100, i * 50
            data = f"spatial_data_{i}"
            infinite_computer.visual_memory_write(x, y, data, "spatial")
            
            ops = renderer.get_viewport_operations()
            yield f"data: {json.dumps({
                'type': 'ir',
                'ops': ops,
                'message': f'Wrote spatial memory at ({x}, {y}): {data}'
            })}\n\n"
            
            time.sleep(0.2)
        
        # Test frame filesystem
        for frame in range(10):
            x, y = frame * 200, 0
            file_data = {"frame": frame, "content": f"File content for frame {frame}"}
            infinite_computer.frame_filesystem_write(x, y, frame, file_data)
            
            ops = renderer.get_viewport_operations()
            yield f"data: {json.dumps({
                'type': 'ir',
                'ops': ops,
                'message': f'Wrote file to frame {frame} at ({x}, {y})'
            })}\n\n"
            
            time.sleep(0.3)
        
        # Test temporal database
        for i in range(15):
            x, y = 0, i * 100
            entity_data = {"id": i, "name": f"Entity_{i}", "value": i * 42}
            infinite_computer.temporal_database_insert(x, y, "entities", f"ent_{i}", entity_data)
            
            ops = renderer.get_viewport_operations()
            yield f"data: {json.dumps({
                'type': 'ir',
                'ops': ops,
                'message': f'Inserted entity {i} at ({x}, {y})'
            })}\n\n"
            
            time.sleep(0.1)
        
        yield f"data: {json.dumps({'type': 'done', 'message': 'Memory test scenario complete'})}\n\n"
    
    return StreamingResponse(
        scenario_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8844, reload=True)