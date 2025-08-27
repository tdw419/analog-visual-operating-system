"""
UVIR Temporal Database Extensions
Integrates temporal database with UVIR visual operations
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import time
from typing import Dict, Any, Optional
from temporal_database import TemporalDatabase, create_sample_temporal_database

class TemporalUVIRBridge:
    def __init__(self):
        self.db = create_sample_temporal_database()
        
    def add_temporal_endpoints(self, app: FastAPI):
        """Add temporal database endpoints to FastAPI app"""
        
        @app.post("/temporal/advance")
        async def advance_temporal_frame():
            """Advance to next temporal frame"""
            self.db.advance_frame()
            current_frame = self.db.current_frame
            
            # Return visualization of current state
            ops = self.db.to_uvir_ops('table_state', current_frame, table_name='employees')
            
            return {
                "type": "ir",
                "frame": current_frame,
                "ops": ops,
                "message": f"Advanced to frame {current_frame}"
            }

        @app.post("/temporal/insert")
        async def temporal_insert(request: Dict[str, Any]):
            """Insert temporal record"""
            table_name = request.get('table')
            entity_id = request.get('entity_id')
            data = request.get('data')
            
            if not table_name or not entity_id or not data:
                return {"error": "Missing required fields: table, entity_id, data"}
            
            record = self.db.insert(table_name, entity_id, data)
            ops = self.db.to_uvir_ops('table_state', self.db.current_frame, table_name=table_name)
            
            return {
                "type": "ir",
                "frame": self.db.current_frame,
                "ops": ops,
                "message": f"Inserted {entity_id} into {table_name}"
            }

        @app.post("/temporal/update")
        async def temporal_update(request: Dict[str, Any]):
            """Update temporal record"""
            table_name = request.get('table')
            entity_id = request.get('entity_id')
            data = request.get('data')
            
            if not table_name or not entity_id or not data:
                return {"error": "Missing required fields: table, entity_id, data"}
            
            record = self.db.update(table_name, entity_id, data)
            ops = self.db.to_uvir_ops('table_state', self.db.current_frame, table_name=table_name)
            
            return {
                "type": "ir",
                "frame": self.db.current_frame,
                "ops": ops,
                "message": f"Updated {entity_id} in {table_name}"
            }

        @app.get("/temporal/query/{table_name}")
        async def temporal_query(table_name: str, frame: Optional[int] = None):
            """Query table at specific frame"""
            query_frame = frame if frame is not None else self.db.current_frame
            
            records = self.db.query_at_frame(table_name, query_frame)
            ops = self.db.to_uvir_ops('table_state', query_frame, table_name=table_name)
            
            return {
                "type": "temporal_query_result",
                "table": table_name,
                "frame": query_frame,
                "record_count": len(records),
                "records": [{"entity_id": r.entity_id, "data": r.data, "valid_from": r.valid_from, "valid_to": r.valid_to} for r in records],
                "ops": ops
            }

        @app.get("/temporal/history/{table_name}/{entity_id}")
        async def get_temporal_history(table_name: str, entity_id: str):
            """Get complete history of entity"""
            history = self.db.query_history(table_name, entity_id)
            ops = self.db.to_uvir_ops('timeline', self.db.current_frame, table_name=table_name, entity_id=entity_id)
            
            return {
                "type": "temporal_history",
                "table": table_name,
                "entity_id": entity_id,
                "history": [{"frame": r.transaction_frame, "operation": r.operation, "data": r.data, "valid_from": r.valid_from, "valid_to": r.valid_to} for r in history],
                "ops": ops
            }

        @app.post("/temporal/aggregate")
        async def temporal_aggregate(request: Dict[str, Any]):
            """Temporal aggregate query"""
            table_name = request.get('table')
            field = request.get('field')
            start_frame = request.get('start_frame', 0)
            end_frame = request.get('end_frame', self.db.current_frame)
            
            result = self.db.temporal_aggregate(table_name, field, start_frame, end_frame)
            ops = self.db.to_uvir_ops('aggregate', self.db.current_frame, 
                                      table_name=table_name, field=field, 
                                      start_frame=start_frame, end_frame=end_frame)
            
            return {
                "type": "temporal_aggregate",
                "result": result,
                "ops": ops
            }

        @app.post("/temporal/time_travel")
        async def time_travel(request: Dict[str, Any]):
            """Jump to specific frame"""
            target_frame = request.get('frame', 0)
            self.db.set_frame(target_frame)
            ops = self.db.to_uvir_ops('table_state', target_frame, table_name='employees')
            
            return {
                "type": "ir",
                "frame": target_frame,
                "ops": ops,
                "message": f"Time traveled to frame {target_frame}"
            }

        @app.get("/temporal/stats")
        async def get_temporal_stats():
            """Get temporal database statistics"""
            stats = self.db.get_database_stats()
            
            # Create visual representation of stats
            ops = [
                {"op": "TEXT", "x": 20, "y": 20, "text": "🕰️ Temporal Database Statistics", "color": "#FFFF00", "size": 18},
                {"op": "TEXT", "x": 20, "y": 50, "text": f"Current Frame: {stats['current_frame']}", "color": "#00FF00", "size": 14},
                {"op": "TEXT", "x": 20, "y": 75, "text": f"Total Tables: {stats['total_tables']}", "color": "#00FFFF", "size": 14},
                {"op": "TEXT", "x": 20, "y": 100, "text": f"Total Records: {stats['total_records']}", "color": "#FFAA00", "size": 14},
            ]
            
            y_offset = 140
            for table_name, table_stats in stats['tables'].items():
                ops.extend([
                    {"op": "TEXT", "x": 40, "y": y_offset, "text": f"📊 {table_name}:", "color": "#FFFFFF", "size": 12},
                    {"op": "TEXT", "x": 60, "y": y_offset + 20, "text": f"Active: {table_stats['active_records']}", "color": "#00FF00", "size": 10},
                    {"op": "TEXT", "x": 160, "y": y_offset + 20, "text": f"Versions: {table_stats['total_versions']}", "color": "#AAAAAA", "size": 10},
                ])
                y_offset += 50
            
            return {
                "type": "temporal_stats",
                "stats": stats,
                "ops": ops
            }

        @app.post("/temporal/scenario")
        async def run_temporal_scenario():
            """Run a demo scenario showing temporal database evolution"""
            
            def scenario_generator():
                scenarios = [
                    {"frame": 5, "action": "update", "table": "employees", "id": "emp1", "data": {"salary": 65000}, "desc": "Alice gets promotion"},
                    {"frame": 8, "action": "insert", "table": "employees", "id": "emp4", "data": {"id": 4, "name": "Diana", "salary": 48000, "department": "Marketing", "age": 24}, "desc": "New hire: Diana joins Marketing"},
                    {"frame": 12, "action": "update", "table": "departments", "id": "dept1", "data": {"budget": 600000}, "desc": "Engineering budget increased"},
                    {"frame": 15, "action": "update", "table": "employees", "id": "emp2", "data": {"department": "Sales", "salary": 58000}, "desc": "Bob transfers to Sales"},
                    {"frame": 20, "action": "delete", "table": "employees", "id": "emp3", "desc": "Charlie leaves the company"},
                    {"frame": 25, "action": "insert", "table": "departments", "id": "dept3", "data": {"id": 3, "name": "Research", "budget": 400000, "manager_id": 4}, "desc": "New Research department created"},
                ]
                
                for scenario in scenarios:
                    self.db.set_frame(scenario["frame"])
                    
                    if scenario["action"] == "insert":
                        self.db.insert(scenario["table"], scenario["id"], scenario["data"])
                    elif scenario["action"] == "update":
                        self.db.update(scenario["table"], scenario["id"], scenario["data"])
                    elif scenario["action"] == "delete":
                        self.db.delete(scenario["table"], scenario["id"])
                    
                    ops = self.db.to_uvir_ops('table_state', scenario["frame"], table_name='employees')
                    
                    # Add scenario description to visualization
                    ops.insert(1, {
                        "op": "TEXT", "x": 20, "y": 50,
                        "text": f"🎬 {scenario['desc']}",
                        "color": "#FF8800", "size": 14
                    })
                    
                    event_data = {
                        "type": "ir",
                        "frame": scenario["frame"],
                        "ops": ops,
                        "scenario": scenario["desc"]
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                    time.sleep(1.5)  # 1.5 second between frames
                    
                yield f"data: {json.dumps({'type': 'done', 'message': 'Temporal scenario complete'})}\n\n"
            
            return StreamingResponse(
                scenario_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )

        @app.post("/temporal/sql")
        async def execute_temporal_sql(request: Dict[str, Any]):
            """Execute temporal SQL-like queries"""
            query = request.get('query', '').upper().strip()
            
            try:
                if "AS OF FRAME" in query:
                    # Parse frame number
                    parts = query.split("AS OF FRAME")
                    if len(parts) == 2:
                        frame = int(parts[1].strip())
                        if "FROM employees" in query:
                            records = self.db.query_at_frame('employees', frame)
                            ops = self.db.to_uvir_ops('table_state', frame, table_name='employees')
                        elif "FROM departments" in query:
                            records = self.db.query_at_frame('departments', frame)
                            ops = self.db.to_uvir_ops('table_state', frame, table_name='departments')
                        else:
                            return {"error": "Unsupported table in query"}
                        
                        return {
                            "type": "temporal_sql_result",
                            "query": query,
                            "frame": frame,
                            "record_count": len(records),
                            "ops": ops
                        }
                
                elif "HISTORY OF" in query:
                    # Parse entity ID
                    parts = query.split("HISTORY OF")
                    if len(parts) == 2:
                        entity_parts = parts[1].strip().split("IN")
                        if len(entity_parts) == 2:
                            entity_id = entity_parts[0].strip()
                            table_name = entity_parts[1].strip()
                            
                            history = self.db.query_history(table_name, entity_id)
                            ops = self.db.to_uvir_ops('timeline', self.db.current_frame, 
                                                     table_name=table_name, entity_id=entity_id)
                            
                            return {
                                "type": "temporal_sql_result",
                                "query": query,
                                "history_count": len(history),
                                "ops": ops
                            }
                
                else:
                    return {"error": f"Unsupported temporal query: {query}"}
                    
            except Exception as e:
                return {"error": f"Query execution error: {str(e)}"}

# Example usage in existing server.py
"""
To integrate with your existing server.py, add these lines:

from temporal_database_uvir import TemporalUVIRBridge

# Create temporal bridge
temporal_bridge = TemporalUVIRBridge()

# Add temporal endpoints to your FastAPI app
temporal_bridge.add_temporal_endpoints(app)
"""