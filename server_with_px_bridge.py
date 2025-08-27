"""
Enhanced Infinite UVIR Server with PX Bridge Integration
Provides dual UVIR (human UI) + PXLang (AI substrate) output with HSTP streaming
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import uuid
import os

# Import our existing modules
from infinite_visual_computer import InfiniteVisualComputer, ChunkCoordinate, PixelCoordinate
from px_bridge import PXBridge, TemporalPXBridge, HSTPPublisher

app = FastAPI(title="Infinite Visual Computer with PX Bridge", description="UVIR + PXLang Unified System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
infinite_computer = InfiniteVisualComputer(chunk_size=64, max_loaded_chunks=100)
px_bridge = PXBridge(width=512, height=512)
hstp_server = None

# Temporal Database (simplified for integration)
class TemporalRecord:
    def __init__(self, entity_id: str, data: Dict[str, Any], valid_from: int, valid_to: Optional[int] = None):
        self.entity_id = entity_id
        self.data = data
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.transaction_frame = valid_from

class TemporalDatabase:
    def __init__(self):
        self.tables: Dict[str, List[TemporalRecord]] = {}
        self.current_frame = 0
    
    def insert(self, table: str, entity_id: str, data: Dict[str, Any]):
        if table not in self.tables:
            self.tables[table] = []
        
        record = TemporalRecord(entity_id, data, self.current_frame)
        self.tables[table].append(record)
        return record
    
    def query_at_frame(self, table: str, frame: int) -> List[TemporalRecord]:
        if table not in self.tables:
            return []
        
        return [r for r in self.tables[table] 
                if r.valid_from <= frame and (r.valid_to is None or r.valid_to > frame)]
    
    def set_frame(self, frame: int):
        self.current_frame = frame
        return frame
    
    def advance_frame(self):
        self.current_frame += 1
        return self.current_frame
    
    def to_uvir_ops(self, view_type: str, frame: int, **kwargs) -> List[Dict[str, Any]]:
        """Generate UVIR operations for visualization"""
        ops = []
        
        if view_type == "table_state":
            table_name = kwargs.get("table_name", "users")
            records = self.query_at_frame(table_name, frame)
            
            # Table header
            ops.append({
                "op": "TEXT",
                "x": 50,
                "y": 50,
                "text": f"{table_name.upper()} (Frame {frame})",
                "color": "#FFFF00",
                "size": 16
            })
            
            # Table background
            ops.append({
                "op": "RECT",
                "x": 40,
                "y": 70,
                "w": 400,
                "h": len(records) * 25 + 40,
                "color": "#333333",
                "fill": True
            })
            
            # Records
            for i, record in enumerate(records):
                y_pos = 90 + (i * 25)
                
                # Record data
                data_text = f"{record.entity_id}: {json.dumps(record.data)[:50]}"
                ops.append({
                    "op": "TEXT",
                    "x": 50,
                    "y": y_pos,
                    "text": data_text,
                    "color": "#00FF00",
                    "size": 12
                })
                
                # Frame info
                frame_text = f"F{record.valid_from}"
                ops.append({
                    "op": "TEXT",
                    "x": 400,
                    "y": y_pos,
                    "text": frame_text,
                    "color": "#AAAAAA",
                    "size": 10
                })
        
        elif view_type == "executive_summary":
            summary = px_bridge.get_executive_summary()
            
            # Executive Summary Header
            ops.append({
                "op": "TEXT",
                "x": 500,
                "y": 50,
                "text": "PX EXECUTIVE SUMMARY",
                "color": "#00FFFF",
                "size": 14
            })
            
            # System Health
            health_color = "#00FF00" if summary["system_health"] == "operational" else "#FF0000"
            ops.append({
                "op": "TEXT",
                "x": 500,
                "y": 80,
                "text": f"Health: {summary['system_health'].upper()}",
                "color": health_color,
                "size": 12
            })
            
            # Key Metrics
            metrics = summary["metrics"]
            y_offset = 110
            for key, value in metrics.items():
                ops.append({
                    "op": "TEXT",
                    "x": 500,
                    "y": y_offset,
                    "text": f"{key.replace('_', ' ').title()}: {value}",
                    "color": "#CCCCCC",
                    "size": 10
                })
                y_offset += 20
            
            # Recent Activity
            ops.append({
                "op": "TEXT",
                "x": 500,
                "y": y_offset + 10,
                "text": "RECENT ACTIVITY:",
                "color": "#FFAA00",
                "size": 12
            })
            
            y_offset += 40
            for activity in summary["recent_activity"][:3]:  # Show top 3
                ops.append({
                    "op": "TEXT",
                    "x": 500,
                    "y": y_offset,
                    "text": f"• {activity['key'][:25]}...",
                    "color": "#DDDDDD",
                    "size": 9
                })
                y_offset += 15
        
        return ops

class FrameFilesystem:
    def __init__(self):
        self.frames: Dict[int, Dict[str, Any]] = {}
        self.current_frame = 0
    
    def write_frame(self, frame: int, data: Dict[str, Any]):
        self.frames[frame] = data
        return data
    
    def read_frame(self, frame: int):
        return self.frames.get(frame)

# Global instances for temporal system
temporal_db = TemporalDatabase()
frame_fs = FrameFilesystem()
temporal_px_bridge = TemporalPXBridge(temporal_db, frame_fs)

# Initialize sample data
def initialize_sample_data():
    """Initialize sample temporal data"""
    # Users table
    temporal_db.insert("users", "user1", {"name": "Alice", "age": 25, "role": "admin"})
    temporal_db.insert("users", "user2", {"name": "Bob", "age": 30, "role": "user"})
    
    # Departments table  
    temporal_db.insert("departments", "eng", {"name": "Engineering", "size": 50})
    temporal_db.insert("departments", "sales", {"name": "Sales", "size": 25})
    
    px_bridge.add_ztxt_entry("system_init", "Temporal Visual Computer initialized with sample data")

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
        
        for connection in connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.send_text(message)
            except:
                connections.remove(connection)

manager = ConnectionManager()

# Pydantic models
class TemporalInsertRequest(BaseModel):
    table: str
    entity_id: str
    data: Dict[str, Any]
    world_x: Optional[int] = 0
    world_y: Optional[int] = 0

class TemporalQueryRequest(BaseModel):
    table: str
    frame: Optional[int] = None

class TimeAdvanceRequest(BaseModel):
    steps: int = 1

class InfinitePixelRequest(BaseModel):
    world_x: int
    world_y: int
    color: str = "#00FF00"

# API Endpoints

@app.get("/")
async def get_root():
    return {
        "message": "Infinite Visual Computer with PX Bridge", 
        "version": "2.0.0",
        "features": ["UVIR", "PXLang", "HSTP", "Temporal_Database", "Infinite_Space"]
    }

@app.websocket("/ws")
async def websocket_uvir(websocket: WebSocket):
    """Main UVIR WebSocket for human UI"""
    await manager.connect(websocket, "uvir")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "viewport_change":
                # Handle viewport changes for infinite space navigation
                world_x = message["world_x"]
                world_y = message["world_y"]
                zoom = message.get("zoom", 1.0)
                
                # Generate viewport-specific UVIR ops
                ops = []
                ops.append({
                    "op": "TEXT",
                    "x": 10,
                    "y": 10,
                    "text": f"Position: ({world_x}, {world_y}) Zoom: {zoom:.1f}x",
                    "color": "#FFFF00",
                    "size": 12
                })
                
                # Add chunk visualization
                chunk_x, chunk_y = world_x // infinite_computer.chunk_size, world_y // infinite_computer.chunk_size
                ops.append({
                    "op": "RECT",
                    "x": 100,
                    "y": 100,
                    "w": 64,
                    "h": 64,
                    "color": "#333333",
                    "fill": False
                })
                
                ops.append({
                    "op": "TEXT",
                    "x": 132,
                    "y": 132,
                    "text": f"Chunk ({chunk_x},{chunk_y})",
                    "color": "#AAAAAA",
                    "size": 8
                })
                
                response = {"type": "ir", "ops": ops}
                await websocket.send_text(json.dumps(response))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/hstp")
async def websocket_hstp(websocket: WebSocket):
    """HSTP WebSocket for AI agents"""
    await manager.connect(websocket, "hstp")
    
    # Send initial HSTP handshake
    handshake = {
        "channel": "PXLang_Pixel_Stream",
        "protocol": "HSTP/1.0",
        "capabilities": ["pixels", "ztxt", "temporal_sync"],
        "timestamp": time.time()
    }
    await websocket.send_text(json.dumps(handshake))
    
    try:
        while True:
            # Keep connection alive and handle agent requests
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Temporal Database Endpoints with PX Bridge Integration

@app.post("/temporal/insert")
async def temporal_insert(request: TemporalInsertRequest):
    """Insert temporal record with PX Bridge mirroring"""
    
    # Execute temporal operation
    result = await temporal_px_bridge.handle_temporal_operation("INSERT", {
        "table": request.table,
        "entity_id": request.entity_id,
        "data": request.data,
        "world_x": request.world_x,
        "world_y": request.world_y
    })
    
    # Broadcast UVIR to human UI
    await manager.broadcast(json.dumps({
        "type": "ir",
        "ops": result["uvir_ops"],
        "event": "temporal_insert"
    }), "uvir")
    
    # Broadcast HSTP to AI agents
    await manager.broadcast(json.dumps({
        "type": "hstp_packet",
        "px_metadata": result["px_metadata"],
        "frame": temporal_db.current_frame
    }), "hstp")
    
    return {
        "success": True,
        "entity_id": request.entity_id,
        "table": request.table,
        "frame": temporal_db.current_frame,
        "px_integration": result["px_metadata"]
    }

@app.get("/temporal/query/{table}")
async def temporal_query(table: str, frame: Optional[int] = None):
    """Query temporal data with visualization"""
    
    result = await temporal_px_bridge.handle_temporal_operation("QUERY", {
        "table": table,
        "frame": frame or temporal_db.current_frame
    })
    
    return {
        "table": table,
        "frame": frame or temporal_db.current_frame,
        "records": result["temporal_result"],
        "ops": result["uvir_ops"],
        "px_metadata": result["px_metadata"]
    }

@app.post("/temporal/time_travel")
async def time_travel(request: Dict[str, int]):
    """Time travel with PX synchronization"""
    target_frame = request.get("target_frame", 0)
    
    result = await temporal_px_bridge.handle_temporal_operation("TIME_TRAVEL", {
        "target_frame": target_frame
    })
    
    px_bridge.current_frame = target_frame
    
    await manager.broadcast(json.dumps({
        "type": "ir",
        "ops": result["uvir_ops"],
        "event": "time_travel",
        "frame": target_frame
    }), "uvir")
    
    return {
        "success": True,
        "target_frame": target_frame,
        "current_frame": temporal_db.current_frame,
        "ops": result["uvir_ops"]
    }

@app.post("/temporal/advance")
async def advance_time(request: Optional[TimeAdvanceRequest] = None):
    """Advance temporal frame with PX sync"""
    steps = request.steps if request else 1
    
    old_frame = temporal_db.current_frame
    for _ in range(steps):
        temporal_db.advance_frame()
        px_bridge.advance_frame()
    
    # Generate updated visualization
    ops = temporal_db.to_uvir_ops("table_state", temporal_db.current_frame, table_name="users")
    executive_ops = temporal_db.to_uvir_ops("executive_summary", temporal_db.current_frame)
    
    # Combine ops
    all_ops = ops + executive_ops
    
    # Mirror to PX Bridge
    px_result = px_bridge.write_operations(all_ops, {
        "operation": "ADVANCE_TIME",
        "old_frame": old_frame,
        "new_frame": temporal_db.current_frame
    })
    
    # Publish HSTP update
    await px_bridge.hstp_publish({
        "operation": "advance_time",
        "steps": steps
    })
    
    return {
        "operation": "ADVANCE_TIME",
        "old_frame": old_frame,
        "current_frame": temporal_db.current_frame,
        "ops": all_ops,
        "px_integration": px_result
    }

# PX Bridge Specific Endpoints

@app.get("/px/executive_summary")
async def get_executive_summary():
    """Get PX executive summary for human oversight"""
    summary = px_bridge.get_executive_summary()
    ops = temporal_db.to_uvir_ops("executive_summary", temporal_db.current_frame)
    
    return {
        "summary": summary,
        "ops": ops,
        "timestamp": time.time()
    }

@app.post("/px/export_digest")
async def export_px_digest():
    """Export current state as .pxdigest file"""
    digest_path = temporal_px_bridge.export_combined_state()
    
    return {
        "success": True,
        "digest_path": digest_path,
        "frame": temporal_db.current_frame,
        "timestamp": time.time()
    }

@app.get("/px/download_digest")
async def download_digest():
    """Download latest .pxdigest file"""
    digest_path = px_bridge.export_digest("latest_export.pxdigest")
    
    return FileResponse(
        path=digest_path,
        media_type="application/octet-stream",
        filename=f"temporal_visual_computer_frame_{temporal_db.current_frame}.pxdigest"
    )

@app.post("/px/import_digest")
async def import_px_digest(request: Request):
    """Import .pxdigest file to restore state"""
    # This would handle file upload in a real implementation
    return {"message": "Import endpoint ready for implementation"}

# Infinite Space Endpoints (existing)

@app.post("/infinite/pixel")
async def set_infinite_pixel(request: InfinitePixelRequest):
    """Set pixel in infinite space with PX mirroring"""
    
    # Parse color
    color_str = request.color
    if color_str.startswith("#"):
        r = int(color_str[1:3], 16)
        g = int(color_str[3:5], 16)
        b = int(color_str[5:7], 16)
        a = 255
    else:
        r, g, b, a = 255, 255, 255, 255
    
    # Set in infinite computer
    infinite_computer.set_world_pixel(request.world_x, request.world_y, (r, g, b, a))
    
    # Create UVIR representation
    uvir_ops = [{
        "op": "RECT",
        "x": 200,
        "y": 200,
        "w": 4,
        "h": 4,
        "color": color_str,
        "fill": True
    }]
    
    # Mirror to PX Bridge
    px_result = px_bridge.write_operations(uvir_ops, {
        "operation": "SET_INFINITE_PIXEL",
        "world_x": request.world_x,
        "world_y": request.world_y,
        "color": color_str
    })
    
    # Broadcast updates
    await manager.broadcast(json.dumps({
        "type": "ir",
        "ops": uvir_ops,
        "event": "pixel_set"
    }), "uvir")
    
    return {
        "success": True,
        "world_x": request.world_x,
        "world_y": request.world_y,
        "color": color_str,
        "px_integration": px_result
    }

@app.get("/infinite/stats")
async def get_infinite_stats():
    """Get infinite computer statistics"""
    infinite_stats = infinite_computer.get_statistics()
    px_summary = px_bridge.get_executive_summary()
    
    return {
        "infinite_computer": infinite_stats,
        "px_substrate": px_summary,
        "integration": {
            "uvir_px_sync": True,
            "hstp_active": len(manager.hstp_connections) > 0,
            "temporal_frame": temporal_db.current_frame,
            "px_frame": px_bridge.current_frame
        }
    }

# Streaming Scenarios

@app.get("/temporal/scenario")
async def run_temporal_scenario():
    """Run temporal evolution scenario with dual UVIR/HSTP streaming"""
    
    def generate_scenario():
        try:
            yield f"data: {json.dumps({'type': 'scenario_start', 'message': 'Starting temporal evolution scenario'})}\n\n"
            
            # Scenario: Company growth over time
            for frame in range(10):
                temporal_db.set_frame(frame)
                
                # Add employees over time
                if frame % 2 == 0:
                    temporal_db.insert("employees", f"emp_{frame}", {
                        "name": f"Employee_{frame}",
                        "department": "Engineering" if frame % 3 == 0 else "Sales",
                        "hire_date": frame
                    })
                
                # Generate visualization
                ops = temporal_db.to_uvir_ops("table_state", frame, table_name="employees")
                executive_ops = temporal_db.to_uvir_ops("executive_summary", frame)
                all_ops = ops + executive_ops
                
                # Mirror to PX
                px_result = px_bridge.write_operations(all_ops, {
                    "scenario_step": frame,
                    "operation": "company_growth"
                })
                
                scenario_data = {
                    "type": "ir",
                    "frame": frame,
                    "ops": all_ops,
                    "px_integration": px_result,
                    "message": f"Company growth: Frame {frame}, {len(temporal_db.query_at_frame('employees', frame))} employees"
                }
                
                yield f"data: {json.dumps(scenario_data)}\n\n"
                time.sleep(0.5)
            
            yield f"data: {json.dumps({'type': 'scenario_complete', 'message': 'Temporal scenario completed'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_scenario(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# Initialize and startup
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    global hstp_server
    
    # Initialize sample data
    initialize_sample_data()
    
    # Start HSTP server for AI agents
    try:
        hstp_server = await px_bridge.hstp_publisher.start_server("localhost", 8845)
        print("HSTP server started on port 8845")
    except Exception as e:
        print(f"Failed to start HSTP server: {e}")
    
    print("Infinite Visual Computer with PX Bridge initialized")
    print("- UVIR endpoint: ws://localhost:8844/ws")
    print("- HSTP endpoint: ws://localhost:8845")
    print("- PX Bridge: Active")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8844, reload=True)