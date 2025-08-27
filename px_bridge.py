"""
PX Bridge: Integrates Temporal Visual Database with PXOS Pixel Supercomputer
Converts UVIR ops to PXLang, manages .pxdigest files, and provides HSTP streaming
"""

import json
import time
import zlib
import struct
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import asyncio
import websockets
import base64
import hashlib
import os

@dataclass
class PXLangOp:
    """PXLang operation for PXOS substrate"""
    op: str
    x: Optional[int] = None
    y: Optional[int] = None
    r: Optional[int] = None
    g: Optional[int] = None
    b: Optional[int] = None
    a: Optional[int] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ZTXTEntry:
    """zTXt metadata entry for AI/agent consumption"""
    key: str
    text: str
    compressed: bool = True
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class PXDigestState:
    """Complete state of a .pxdigest file"""
    width: int = 512
    height: int = 512
    pixels: bytearray = None
    ztxt_entries: List[ZTXTEntry] = None
    frame_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.pixels is None:
            self.pixels = bytearray(self.width * self.height * 4)  # RGBA
        if self.ztxt_entries is None:
            self.ztxt_entries = []
        if self.frame_metadata is None:
            self.frame_metadata = {}

class HSTPPublisher:
    """HSTP (Hierarchical Streaming Transport Protocol) publisher for AI agents"""
    
    def __init__(self, channel_name: str = "PXLang_Pixel_Stream"):
        self.channel_name = channel_name
        self.clients: List[websockets.WebSocketServerProtocol] = []
        self.packet_id = 0
        
    async def start_server(self, host: str = "localhost", port: int = 8845):
        """Start HSTP WebSocket server"""
        async def handle_client(websocket, path):
            self.clients.append(websocket)
            try:
                await websocket.wait_closed()
            finally:
                self.clients.remove(websocket)
        
        return await websockets.serve(handle_client, host, port)
    
    async def publish_packet(self, pixels: bytes, ztxt_delta: List[ZTXTEntry], frame: int):
        """Publish HSTP packet to all connected clients"""
        packet = {
            "channel": self.channel_name,
            "packet_id": self.packet_id,
            "frame": frame,
            "timestamp": time.time(),
            "pixels_base64": base64.b64encode(pixels).decode('utf-8'),
            "ztxt_delta": [asdict(entry) for entry in ztxt_delta]
        }
        
        packet_json = json.dumps(packet)
        self.packet_id += 1
        
        # Send to all connected clients
        if self.clients:
            disconnected = []
            for client in self.clients:
                try:
                    await client.send(packet_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.append(client)
            
            # Clean up disconnected clients
            for client in disconnected:
                self.clients.remove(client)

class PXBridge:
    """Bridge between Temporal Visual Database and PXOS Substrate"""
    
    def __init__(self, width: int = 512, height: int = 512):
        self.digest_state = PXDigestState(width, height)
        self.hstp_publisher = HSTPPublisher()
        self.current_frame = 0
        self.frame_deltas: Dict[int, List[PXLangOp]] = defaultdict(list)
        self.ztxt_buffer: List[ZTXTEntry] = []
        
    def uvir_to_pxlang(self, uvir_ops: List[Dict[str, Any]], frame: int) -> List[PXLangOp]:
        """Convert UVIR operations to PXLang operations"""
        pxlang_ops = []
        
        for op in uvir_ops:
            op_type = op.get("op", "")
            
            if op_type == "RECT":
                # Convert RECT to SET_PX operations
                x = op.get("x", 0)
                y = op.get("y", 0)
                w = op.get("w", 1)
                h = op.get("h", 1)
                color = self._parse_color(op.get("color", "#FFFFFF"))
                
                # Generate SET_PX for each pixel in rectangle
                for dy in range(h):
                    for dx in range(w):
                        if 0 <= x + dx < self.digest_state.width and 0 <= y + dy < self.digest_state.height:
                            pxlang_ops.append(PXLangOp(
                                op="SET_PX",
                                x=x + dx,
                                y=y + dy,
                                r=color[0],
                                g=color[1],
                                b=color[2],
                                a=color[3],
                                metadata={"source_op": op_type, "frame": frame}
                            ))
            
            elif op_type == "TEXT":
                # Convert TEXT to zTXt entry + visualization pixels
                text = op.get("text", "")
                x = op.get("x", 0)
                y = op.get("y", 0)
                color = self._parse_color(op.get("color", "#00FF00"))
                
                # Add zTXt entry for AI consumption
                ztxt_key = f"text_{x}_{y}_{frame}"
                self.add_ztxt_entry(ztxt_key, text)
                
                # Simple text visualization (could be enhanced with font rendering)
                text_pixels = self._text_to_pixels(text, x, y, color)
                pxlang_ops.extend(text_pixels)
            
            elif op_type == "TEMPORAL_QUERY":
                # Convert temporal query results to zTXt entries
                query_data = op.get("data", {})
                query_text = f"TEMPORAL_QUERY: {json.dumps(query_data)}"
                self.add_ztxt_entry(f"temporal_query_{frame}", query_text)
                
                # Visual heat map of query results
                result_count = query_data.get("count", 0)
                heat_color = self._get_heat_color(result_count)
                center_x = self.digest_state.width // 2
                center_y = self.digest_state.height // 2
                
                pxlang_ops.append(PXLangOp(
                    op="SET_PX",
                    x=center_x,
                    y=center_y,
                    r=heat_color[0],
                    g=heat_color[1],
                    b=heat_color[2],
                    a=heat_color[3],
                    metadata={"temporal_query": True, "result_count": result_count}
                ))
        
        return pxlang_ops
    
    def write_operations(self, uvir_ops: List[Dict[str, Any]], temporal_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Write operations to digest and return metadata"""
        # Convert UVIR to PXLang
        pxlang_ops = self.uvir_to_pxlang(uvir_ops, self.current_frame)
        
        # Apply PXLang operations to digest pixels
        digest_offset = self._apply_pxlang_ops(pxlang_ops)
        
        # Handle temporal events
        ztxt_keys = []
        if temporal_event:
            event_key = f"temporal_event_{self.current_frame}"
            event_text = json.dumps(temporal_event)
            self.add_ztxt_entry(event_key, event_text)
            ztxt_keys.append(event_key)
        
        # Store frame delta
        self.frame_deltas[self.current_frame] = pxlang_ops
        
        return {
            "digest_offset": digest_offset,
            "ztxt_keys": ztxt_keys,
            "pxlang_ops_count": len(pxlang_ops)
        }
    
    def add_ztxt_entry(self, key: str, text: str, compressed: bool = True):
        """Add zTXt entry for AI/agent consumption"""
        entry = ZTXTEntry(key=key, text=text, compressed=compressed)
        self.digest_state.ztxt_entries.append(entry)
        self.ztxt_buffer.append(entry)
    
    def advance_frame(self):
        """Advance to next frame and prepare for new operations"""
        self.current_frame += 1
        self.ztxt_buffer.clear()
    
    async def hstp_publish(self, additional_metadata: Optional[Dict[str, Any]] = None):
        """Publish current frame delta via HSTP"""
        # Get current frame pixels (could optimize to send only changed regions)
        pixels = bytes(self.digest_state.pixels)
        
        # Prepare zTXt delta
        ztxt_delta = self.ztxt_buffer.copy()
        
        # Add frame metadata
        if additional_metadata:
            metadata_text = json.dumps(additional_metadata)
            ztxt_delta.append(ZTXTEntry(f"frame_metadata_{self.current_frame}", metadata_text))
        
        await self.hstp_publisher.publish_packet(pixels, ztxt_delta, self.current_frame)
    
    def export_digest(self, output_path: Optional[str] = None) -> bytes:
        """Export current state as .pxdigest file"""
        if output_path is None:
            output_path = f"temporal_visual_computer_{self.current_frame}.pxdigest"
        
        # Create digest structure
        digest_data = {
            "version": "1.0",
            "width": self.digest_state.width,
            "height": self.digest_state.height,
            "current_frame": self.current_frame,
            "created": time.time(),
            "pixels": base64.b64encode(self.digest_state.pixels).decode('utf-8'),
            "ztxt_entries": [asdict(entry) for entry in self.digest_state.ztxt_entries],
            "frame_deltas": {str(k): [asdict(op) for op in v] for k, v in self.frame_deltas.items()},
            "metadata": self.digest_state.frame_metadata
        }
        
        # Compress and save
        digest_json = json.dumps(digest_data, separators=(',', ':'))
        compressed_digest = zlib.compress(digest_json.encode('utf-8'))
        
        with open(output_path, 'wb') as f:
            # Write magic header for .pxdigest
            f.write(b'PXDIG1.0')
            f.write(struct.pack('<I', len(compressed_digest)))
            f.write(compressed_digest)
        
        return compressed_digest
    
    def import_digest(self, digest_path: str):
        """Import .pxdigest file and restore state"""
        with open(digest_path, 'rb') as f:
            # Read magic header
            magic = f.read(8)
            if magic != b'PXDIG1.0':
                raise ValueError("Invalid .pxdigest file format")
            
            # Read compressed data
            data_length = struct.unpack('<I', f.read(4))[0]
            compressed_data = f.read(data_length)
            
            # Decompress and parse
            digest_json = zlib.decompress(compressed_data).decode('utf-8')
            digest_data = json.loads(digest_json)
            
            # Restore state
            self.digest_state.width = digest_data["width"]
            self.digest_state.height = digest_data["height"]
            self.current_frame = digest_data["current_frame"]
            self.digest_state.pixels = bytearray(base64.b64decode(digest_data["pixels"]))
            
            # Restore zTXt entries
            self.digest_state.ztxt_entries = [
                ZTXTEntry(**entry) for entry in digest_data["ztxt_entries"]
            ]
            
            # Restore frame deltas
            self.frame_deltas = {
                int(k): [PXLangOp(**op) for op in v] 
                for k, v in digest_data["frame_deltas"].items()
            }
            
            self.digest_state.frame_metadata = digest_data.get("metadata", {})
    
    def get_executive_summary(self) -> Dict[str, Any]:
        """Get executive summary for human oversight"""
        # Analyze zTXt entries for key insights
        total_entries = len(self.digest_state.ztxt_entries)
        temporal_queries = len([e for e in self.digest_state.ztxt_entries if e.key.startswith("temporal_query")])
        text_entries = len([e for e in self.digest_state.ztxt_entries if e.key.startswith("text_")])
        events = len([e for e in self.digest_state.ztxt_entries if e.key.startswith("temporal_event")])
        
        # Calculate activity metrics
        total_pixels_set = sum(len(ops) for ops in self.frame_deltas.values())
        active_frames = len(self.frame_deltas)
        
        # Get recent activity
        recent_entries = sorted(self.digest_state.ztxt_entries, key=lambda x: x.timestamp, reverse=True)[:5]
        
        return {
            "system_health": "operational",
            "current_frame": self.current_frame,
            "total_ztxt_entries": total_entries,
            "metrics": {
                "temporal_queries": temporal_queries,
                "text_entries": text_entries,
                "events": events,
                "pixels_modified": total_pixels_set,
                "active_frames": active_frames
            },
            "recent_activity": [
                {
                    "key": entry.key,
                    "timestamp": entry.timestamp,
                    "preview": entry.text[:50] + "..." if len(entry.text) > 50 else entry.text
                }
                for entry in recent_entries
            ],
            "digest_size_kb": len(self.digest_state.pixels) // 1024,
            "uptime_frames": self.current_frame
        }
    
    # Helper methods
    def _parse_color(self, color_str: str) -> Tuple[int, int, int, int]:
        """Parse color string to RGBA tuple"""
        if color_str.startswith("#"):
            color_str = color_str[1:]
            if len(color_str) == 6:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                a = 255
            elif len(color_str) == 8:
                r = int(color_str[0:2], 16)
                g = int(color_str[2:4], 16)
                b = int(color_str[4:6], 16)
                a = int(color_str[6:8], 16)
            else:
                r, g, b, a = 255, 255, 255, 255
        else:
            r, g, b, a = 255, 255, 255, 255
        
        return (r, g, b, a)
    
    def _apply_pxlang_ops(self, pxlang_ops: List[PXLangOp]) -> int:
        """Apply PXLang operations to digest pixels"""
        ops_applied = 0
        
        for op in pxlang_ops:
            if op.op == "SET_PX" and op.x is not None and op.y is not None:
                if 0 <= op.x < self.digest_state.width and 0 <= op.y < self.digest_state.height:
                    pixel_index = (op.y * self.digest_state.width + op.x) * 4
                    
                    self.digest_state.pixels[pixel_index] = op.r or 0
                    self.digest_state.pixels[pixel_index + 1] = op.g or 0
                    self.digest_state.pixels[pixel_index + 2] = op.b or 0
                    self.digest_state.pixels[pixel_index + 3] = op.a or 255
                    
                    ops_applied += 1
        
        return ops_applied
    
    def _text_to_pixels(self, text: str, x: int, y: int, color: Tuple[int, int, int, int]) -> List[PXLangOp]:
        """Convert text to pixel operations (simple bitmap approach)"""
        ops = []
        
        # Simple character mapping (could be enhanced with actual font rendering)
        char_width = 6
        char_height = 8
        
        for i, char in enumerate(text[:20]):  # Limit to 20 characters
            char_x = x + (i * char_width)
            if char_x + char_width >= self.digest_state.width:
                break
            
            # Simple block character representation
            for cy in range(char_height):
                for cx in range(char_width):
                    pixel_x = char_x + cx
                    pixel_y = y + cy
                    
                    if (0 <= pixel_x < self.digest_state.width and 
                        0 <= pixel_y < self.digest_state.height):
                        
                        # Simple pattern based on character ASCII
                        if (cx + cy + ord(char)) % 3 == 0:
                            ops.append(PXLangOp(
                                op="SET_PX",
                                x=pixel_x,
                                y=pixel_y,
                                r=color[0],
                                g=color[1],
                                b=color[2],
                                a=color[3]
                            ))
        
        return ops
    
    def _get_heat_color(self, value: int) -> Tuple[int, int, int, int]:
        """Get heat map color for visualization"""
        # Simple heat map: blue (cold) to red (hot)
        if value == 0:
            return (0, 0, 255, 255)  # Blue
        elif value < 10:
            return (0, 255, 0, 255)  # Green
        elif value < 50:
            return (255, 255, 0, 255)  # Yellow
        else:
            return (255, 0, 0, 255)  # Red

# Example integration with existing temporal system
class TemporalPXBridge:
    """Integration layer between TemporalDatabase and PXBridge"""
    
    def __init__(self, temporal_db, frame_fs):
        self.temporal_db = temporal_db
        self.frame_fs = frame_fs
        self.px_bridge = PXBridge()
        
    async def handle_temporal_operation(self, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle temporal database operation and mirror to PX substrate"""
        
        # Execute original temporal operation
        if operation == "INSERT":
            result = self.temporal_db.insert(data["table"], data["entity_id"], data["data"])
        elif operation == "QUERY":
            result = self.temporal_db.query_at_frame(data["table"], data["frame"])
        elif operation == "TIME_TRAVEL":
            result = self.temporal_db.set_frame(data["target_frame"])
        else:
            result = {"error": f"Unknown operation: {operation}"}
        
        # Generate UVIR for visualization
        uvir_ops = self.temporal_db.to_uvir_ops("table_state", self.temporal_db.current_frame)
        
        # Mirror to PX substrate
        px_result = self.px_bridge.write_operations(uvir_ops, {
            "operation": operation,
            "data": data,
            "result": result
        })
        
        # Publish via HSTP
        await self.px_bridge.hstp_publish({
            "temporal_operation": operation,
            "frame": self.temporal_db.current_frame
        })
        
        return {
            "temporal_result": result,
            "uvir_ops": uvir_ops,
            "px_metadata": px_result
        }
    
    def export_combined_state(self) -> str:
        """Export both temporal state and PX digest"""
        # Export temporal state as JSON
        temporal_export = {
            "frame_filesystem": self.frame_fs.export_frames(),
            "temporal_database": self.temporal_db.export_state(),
            "current_frame": self.temporal_db.current_frame
        }
        
        # Export PX digest
        px_digest_path = f"combined_state_{int(time.time())}.pxdigest"
        self.px_bridge.export_digest(px_digest_path)
        
        # Save temporal JSON alongside
        json_path = px_digest_path.replace('.pxdigest', '_temporal.json')
        with open(json_path, 'w') as f:
            json.dump(temporal_export, f, indent=2)
        
        return px_digest_path

if __name__ == "__main__":
    # Example usage
    bridge = PXBridge(512, 512)
    
    # Simulate UVIR operations
    uvir_ops = [
        {"op": "RECT", "x": 100, "y": 100, "w": 50, "h": 30, "color": "#FF0000"},
        {"op": "TEXT", "x": 200, "y": 200, "text": "Hello PXOS!", "color": "#00FF00"},
        {"op": "TEMPORAL_QUERY", "data": {"count": 42, "table": "users"}}
    ]
    
    # Process operations
    result = bridge.write_operations(uvir_ops, {"operation": "test", "timestamp": time.time()})
    print(f"PX Bridge result: {result}")
    
    # Export digest
    digest_path = bridge.export_digest("test_output.pxdigest")
    print(f"Exported digest: {digest_path}")
    
    # Show executive summary
    summary = bridge.get_executive_summary()
    print(f"Executive Summary: {json.dumps(summary, indent=2)}")