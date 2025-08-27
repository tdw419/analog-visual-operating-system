"""
Infinite Visual Computer Server - UVIR + PX Bridge Integration
Provides REST API and WebSocket endpoints for the infinite visual computer
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
import numpy as np

# Import our modules
from infinite_visual_computer import InfiniteVisualComputer, ChunkCoordinate, PixelCoordinate
from px_bridge import PXBridge, TemporalPXBridge

app = FastAPI(title="Infinite Visual Computer Server", description="UVIR + Infinite Space + PX Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
infinite_computer = InfiniteVisualComputer(chunk_size=64, max_loaded_chunks=100)
px_bridge = PXBridge(width=1024, height=1024)  # Larger for infinite space

# WebSocket connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.hstp_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, connection_type: str = "uvir"):
        await websocket.accept()
        if connection_type == "hstp":
            self.hstp_connections.append(websocket)
        else:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.hstp_connections:
            self.hstp_connections.remove(websocket)

    async def broadcast(self, message: str, connection_type: str = "uvir"):
        connections = self.hstp_connections if connection_type == "hstp" else self.active_connections
        
        for connection in connections[:]:
            try:
                await connection.send_text(message)
            except:
                connections.remove(connection)

manager = ConnectionManager()

# Pydantic models
class ViewportRequest(BaseModel):
    center_x: int
    center_y: int
    width: int = 800
    height: int = 600
    zoom: float = 1.0

class PixelRequest(BaseModel):
    world_x: int
    world_y: int
    color: str = "#00FF00"

class MemoryWriteRequest(BaseModel):
    world_x: int
    world_y: int
    data: Any
    memory_type: str = "spatial"

class FilesystemWriteRequest(BaseModel):
    world_x: int
    world_y: int
    frame: int
    file_data: Any

class DatabaseInsertRequest(BaseModel):
    world_x: int
    world_y: int
    table: str
    entity_id: str
    data: Dict[str, Any]

class DatabaseQueryRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    table: str
    frame: Optional[int] = None

def generate_viewport_uvir_ops(viewport: np.ndarray, center_x: int, center_y: int, 
                              width: int, height: int, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate UVIR operations for viewport visualization"""
    ops = []
    
    # Viewport header
    ops.append({
        "op": "TEXT",
        "x": 10,
        "y": 20,
        "text": f"Infinite Visual Computer - Frame {stats['current_frame']}",
        "color": "#00FFFF",
        "size": 16
    })
    
    # Viewport coordinates
    ops.append({
        "op": "TEXT",
        "x": 10,
        "y": 40,
        "text": f"Center: ({center_x}, {center_y}) | View: {width}x{height}",
        "color": "#FFFF00",
        "size": 12
    })
    
    # Chunk information
    chunk_x, chunk_y = center_x // infinite_computer.chunk_size, center_y // infinite_computer.chunk_size
    ops.append({
        "op": "TEXT",
        "x": 10,
        "y": 60,
        "text": f"Current Chunk: ({chunk_x}, {chunk_y})",
        "color": "#AAAAAA",
        "size": 10
    })
    
    # Statistics
    ops.append({
        "op": "TEXT",
        "x": 10,
        "y": 80,
        "text": f"Loaded Chunks: {stats['loaded_chunks']} | Active: {stats['active_chunks']}",
        "color": "#00FF00",
        "size": 10
    })
    
    # Render viewport pixels as RECT operations
    pixel_size = max(1, int(4 / max(1, width // 200)))  # Scale based on viewport size
    
    for y in range(0, height, pixel_size):
        for x in range(0, width, pixel_size):
            if y < viewport.shape[0] and x < viewport.shape[1]:
                pixel = viewport[y, x]
                if np.sum(pixel[:3]) > 0:  # Only render non-black pixels
                    color = f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}"
                    ops.append({
                        "op": "RECT",
                        "x": 100 + x,
                        "y": 100 + y,
                        "w": pixel_size,
                        "h": pixel_size,
                        "color": color,
                        "fill": True
                    })
    
    # Chunk boundaries visualization
    chunk_size_in_view = infinite_computer.chunk_size
    start_chunk_x = (center_x - width // 2) // infinite_computer.chunk_size
    start_chunk_y = (center_y - height // 2) // infinite_computer.chunk_size
    end_chunk_x = (center_x + width // 2) // infinite_computer.chunk_size
    end_chunk_y = (center_y + height // 2) // infinite_computer.chunk_size
    
    for chunk_x in range(start_chunk_x, end_chunk_x + 2):
        for chunk_y in range(start_chunk_y, end_chunk_y + 2):
            # Calculate screen position of chunk boundary
            world_chunk_x = chunk_x * infinite_computer.chunk_size
            world_chunk_y = chunk_y * infinite_computer.chunk_size
            screen_x = 100 + (world_chunk_x - (center_x - width // 2))
            screen_y = 100 + (world_chunk_y - (center_y - height // 2))
            
            if 100 <= screen_x <= 100 + width and 100 <= screen_y <= 100 + height:
                # Chunk boundary rectangle
                ops.append({
                    "op": "RECT",
                    "x": screen_x,
                    "y": screen_y,
                    "w": min(chunk_size_in_view, 100 + width - screen_x),
                    "h": min(chunk_size_in_view, 100 + height - screen_y),
                    "color": "#333333",
                    "fill": False
                })
                
                # Chunk coordinate label
                if screen_x + 10 < 100 + width and screen_y + 20 < 100 + height:
                    ops.append({
                        "op": "TEXT",
                        "x": screen_x + 5,
                        "y": screen_y + 15,
                        "text": f"({chunk_x},{chunk_y})",
                        "color": "#666666",
                        "size": 8
                    })
    
    return ops

# API Endpoints

@app.get("/")
async def get_root():
    return {
        "message": "Infinite Visual Computer Server",
        "version": "1.0.0",
        "features": ["Infinite_Space", "UVIR", "PX_Bridge", "Chunk_Management"]
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main UVIR WebSocket for infinite space navigation"""
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "viewport_request":
                center_x = message.get("center_x", 0)
                center_y = message.get("center_y", 0)
                width = message.get("width", 800)
                height = message.get("height", 600)
                
                # Get viewport from infinite computer
                viewport = infinite_computer.get_view_window(center_x, center_y, width, height)
                stats = infinite_computer.get_statistics()
                
                # Generate UVIR operations
                ops = generate_viewport_uvir_ops(viewport, center_x, center_y, width, height, stats)
                
                # Send to PX Bridge
                px_result = px_bridge.write_operations(ops, {
                    "operation": "VIEWPORT_UPDATE",
                    "center": (center_x, center_y),
                    "frame": infinite_computer.current_frame
                })
                
                response = {
                    "type": "ir",
                    "ops": ops,
                    "viewport": {
                        "center_x": center_x,
                        "center_y": center_y,
                        "width": width,
                        "height": height
                    },
                    "stats": stats,
                    "px_metadata": px_result
                }
                
                await websocket.send_text(json.dumps(response))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/infinite/pixel")
async def set_infinite_pixel(request: PixelRequest):
    """Set pixel in infinite space"""
    # Parse color
    color_str = request.color
    if color_str.startswith("#"):
        r = int(color_str[1:3], 16)
        g = int(color_str[3:5], 16)
        b = int(color_str[5:7], 16)
        a = 255
    else:
        r, g, b, a = 255, 255, 255, 255
    
    # Set pixel in infinite space
    infinite_computer.set_world_pixel(request.world_x, request.world_y, (r, g, b, a))
    
    # Generate UVIR representation
    ops = [{
        "op": "RECT",
        "x": 400,  # Center of typical viewport
        "y": 300,
        "w": 4,
        "h": 4,
        "color": color_str,
        "fill": True
    }, {
        "op": "TEXT",
        "x": 410,
        "y": 315,
        "text": f"Set ({request.world_x}, {request.world_y})",
        "color": "#FFFF00",
        "size": 10
    }]
    
    # Send to PX Bridge
    px_result = px_bridge.write_operations(ops, {
        "operation": "SET_PIXEL",
        "world_coords": (request.world_x, request.world_y),
        "color": color_str
    })
    
    # Broadcast update
    await manager.broadcast(json.dumps({
        "type": "ir",
        "ops": ops,
        "event": "pixel_set"
    }))
    
    return {
        "success": True,
        "world_x": request.world_x,
        "world_y": request.world_y,
        "color": color_str,
        "px_integration": px_result
    }

@app.post("/infinite/memory/write")
async def write_visual_memory(request: MemoryWriteRequest):
    """Write to visual memory system"""
    infinite_computer.visual_memory_write(
        request.world_x, request.world_y, 
        request.data, request.memory_type
    )
    
    # Generate UVIR ops
    ops = [{
        "op": "TEXT",
        "x": 10,
        "y": 100,
        "text": f"Memory Write: ({request.world_x}, {request.world_y})",
        "color": "#00FFFF",
        "size": 12
    }, {
        "op": "TEXT",
        "x": 10,
        "y": 120,
        "text": f"Type: {request.memory_type} | Data: {str(request.data)[:50]}",
        "color": "#AAAAAA",
        "size": 10
    }]
    
    px_result = px_bridge.write_operations(ops, {
        "operation": "MEMORY_WRITE",
        "coords": (request.world_x, request.world_y),
        "type": request.memory_type
    })
    
    return {
        "success": True,
        "world_coords": (request.world_x, request.world_y),
        "memory_type": request.memory_type,
        "px_integration": px_result
    }

@app.get("/infinite/memory/read")
async def read_visual_memory(world_x: int, world_y: int):
    """Read from visual memory system"""
    memory_data = infinite_computer.visual_memory_read(world_x, world_y)
    
    return {
        "world_coords": (world_x, world_y),
        "memory_data": memory_data
    }

@app.post("/infinite/filesystem/write")
async def write_frame_filesystem(request: FilesystemWriteRequest):
    """Write to frame filesystem"""
    infinite_computer.frame_filesystem_write(
        request.world_x, request.world_y,
        request.frame, request.file_data
    )
    
    ops = [{
        "op": "TEXT",
        "x": 10,
        "y": 140,
        "text": f"File Write: Frame {request.frame} at ({request.world_x}, {request.world_y})",
        "color": "#FFAA00",
        "size": 12
    }]
    
    px_result = px_bridge.write_operations(ops, {
        "operation": "FILESYSTEM_WRITE",
        "coords": (request.world_x, request.world_y),
        "frame": request.frame
    })
    
    return {
        "success": True,
        "frame": request.frame,
        "world_coords": (request.world_x, request.world_y),
        "px_integration": px_result
    }

@app.get("/infinite/filesystem/read")
async def read_frame_filesystem(world_x: int, world_y: int, frame: int):
    """Read from frame filesystem"""
    file_data = infinite_computer.frame_filesystem_read(world_x, world_y, frame)
    
    return {
        "frame": frame,
        "world_coords": (world_x, world_y),
        "file_data": file_data
    }

@app.post("/infinite/database/insert")
async def insert_temporal_database(request: DatabaseInsertRequest):
    """Insert into temporal database"""
    infinite_computer.temporal_database_insert(
        request.world_x, request.world_y,
        request.table, request.entity_id, request.data
    )
    
    ops = [{
        "op": "TEXT",
        "x": 10,
        "y": 160,
        "text": f"DB Insert: {request.table}.{request.entity_id}",
        "color": "#00FF00",
        "size": 12
    }, {
        "op": "TEXT",
        "x": 10,
        "y": 180,
        "text": f"Location: ({request.world_x}, {request.world_y})",
        "color": "#AAAAAA",
        "size": 10
    }]
    
    px_result = px_bridge.write_operations(ops, {
        "operation": "DATABASE_INSERT",
        "table": request.table,
        "entity_id": request.entity_id,
        "coords": (request.world_x, request.world_y)
    })
    
    return {
        "success": True,
        "table": request.table,
        "entity_id": request.entity_id,
        "world_coords": (request.world_x, request.world_y),
        "frame": infinite_computer.current_frame,
        "px_integration": px_result
    }

@app.post("/infinite/database/query")
async def query_temporal_database(request: DatabaseQueryRequest):
    """Query temporal database"""
    frame = request.frame if request.frame is not None else infinite_computer.current_frame
    results = infinite_computer.temporal_database_query(
        (request.x1, request.y1, request.x2, request.y2),
        request.table, frame
    )
    
    # Generate UVIR visualization of query results
    ops = [{
        "op": "TEXT",
        "x": 10,
        "y": 200,
        "text": f"DB Query: {request.table} in region ({request.x1},{request.y1}) to ({request.x2},{request.y2})",
        "color": "#FFFF00",
        "size": 12
    }, {
        "op": "TEXT",
        "x": 10,
        "y": 220,
        "text": f"Frame: {frame} | Results: {len(results)} records",
        "color": "#00FF00",
        "size": 10
    }]
    
    # Visualize query region
    region_width = request.x2 - request.x1
    region_height = request.y2 - request.y1
    ops.append({
        "op": "RECT",
        "x": 300,
        "y": 300,
        "w": min(region_width, 100),
        "h": min(region_height, 100),
        "color": "#FFFF00",
        "fill": False
    })
    
    px_result = px_bridge.write_operations(ops, {
        "operation": "DATABASE_QUERY",
        "table": request.table,
        "region": (request.x1, request.y1, request.x2, request.y2),
        "frame": frame,
        "result_count": len(results)
    })
    
    return {
        "table": request.table,
        "frame": frame,
        "region": (request.x1, request.y1, request.x2, request.y2),
        "results": results,
        "count": len(results),
        "px_integration": px_result
    }

@app.post("/infinite/advance_frame")
async def advance_frame():
    """Advance computational frame"""
    old_frame = infinite_computer.current_frame
    infinite_computer.advance_frame()
    
    stats = infinite_computer.get_statistics()
    
    ops = [{
        "op": "TEXT",
        "x": 10,
        "y": 240,
        "text": f"Frame Advanced: {old_frame} → {infinite_computer.current_frame}",
        "color": "#00FFFF",
        "size": 14
    }, {
        "op": "TEXT",
        "x": 10,
        "y": 260,
        "text": f"Active Chunks: {stats['active_chunks']} | Total Chunks: {stats['loaded_chunks']}",
        "color": "#AAAAAA",
        "size": 10
    }]
    
    px_result = px_bridge.write_operations(ops, {
        "operation": "ADVANCE_FRAME",
        "old_frame": old_frame,
        "new_frame": infinite_computer.current_frame
    })
    
    # Broadcast frame advance
    await manager.broadcast(json.dumps({
        "type": "ir",
        "ops": ops,
        "event": "frame_advance",
        "frame": infinite_computer.current_frame
    }))
    
    return {
        "operation": "ADVANCE_FRAME",
        "old_frame": old_frame,
        "current_frame": infinite_computer.current_frame,
        "statistics": stats,
        "px_integration": px_result
    }

@app.get("/infinite/stats")
async def get_infinite_stats():
    """Get infinite computer statistics"""
    stats = infinite_computer.get_statistics()
    px_summary = px_bridge.get_executive_summary()
    
    return {
        "infinite_computer": stats,
        "px_substrate": px_summary,
        "integration_status": {
            "uvir_active": len(manager.active_connections) > 0,
            "hstp_active": len(manager.hstp_connections) > 0,
            "current_frame": infinite_computer.current_frame,
            "px_frame": px_bridge.current_frame
        }
    }

@app.get("/infinite/scenario")
async def run_infinite_scenario():
    """Run infinite space demonstration scenario"""
    
    def generate_scenario():
        try:
            yield f"data: {json.dumps({'type': 'scenario_start', 'message': 'Starting infinite space scenario'})}\n\n"
            
            # Scenario: Expanding cellular automata across chunks
            for step in range(20):
                # Add some seed patterns
                if step < 5:
                    # Create glider patterns in different chunks
                    base_x = step * 200
                    base_y = step * 150
                    
                    # Glider pattern
                    glider_coords = [(1,0), (2,1), (0,2), (1,2), (2,2)]
                    for dx, dy in glider_coords:
                        infinite_computer.set_world_pixel(
                            base_x + dx, base_y + dy, 
                            (0, 255, 0, 255)
                        )
                
                # Advance frame
                infinite_computer.advance_frame()
                
                # Get current view
                center_x, center_y = step * 50, step * 30
                viewport = infinite_computer.get_view_window(center_x, center_y, 200, 150)
                stats = infinite_computer.get_statistics()
                
                # Generate UVIR ops
                ops = generate_viewport_uvir_ops(viewport, center_x, center_y, 200, 150, stats)
                
                # Add scenario info
                ops.append({
                    "op": "TEXT",
                    "x": 10,
                    "y": 280,
                    "text": f"Scenario Step: {step + 1}/20",
                    "color": "#FF00FF",
                    "size": 12
                })
                
                scenario_data = {
                    "type": "ir",
                    "step": step,
                    "frame": infinite_computer.current_frame,
                    "ops": ops,
                    "message": f"Step {step + 1}: {stats['active_chunks']} active chunks"
                }
                
                yield f"data: {json.dumps(scenario_data)}\n\n"
                time.sleep(0.3)
            
            yield f"data: {json.dumps({'type': 'scenario_complete', 'message': 'Infinite scenario completed'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_scenario(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# Initialize system
@app.on_event("startup")
async def startup_event():
    """Initialize infinite visual computer"""
    print("Infinite Visual Computer Server starting...")
    print(f"- Chunk size: {infinite_computer.chunk_size}x{infinite_computer.chunk_size}")
    print(f"- Max loaded chunks: {infinite_computer.max_loaded_chunks}")
    print(f"- PX Bridge: Active")
    print(f"- Initial statistics: {infinite_computer.get_statistics()}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8845, reload=True)