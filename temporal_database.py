"""
Temporal Database Engine for Frame-Based Visual Storage
Each frame becomes a temporal snapshot in the database timeline
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json
import time
from datetime import datetime
import bisect

@dataclass
class TemporalRecord:
    entity_id: str
    table_name: str
    data: Dict[str, Any]
    valid_from: int  # Frame number
    valid_to: Optional[int] = None  # None means "current"
    transaction_frame: int = 0  # When this record was created
    operation: str = 'INSERT'  # INSERT, UPDATE, DELETE

class TemporalDatabase:
    def __init__(self, max_frames: int = 100):
        self.max_frames = max_frames
        self.tables: Dict[str, List[TemporalRecord]] = {}
        self.current_frame = 0
        self.schemas: Dict[str, Dict[str, str]] = {}
        
    def create_table(self, table_name: str, schema: Dict[str, str]):
        """Create a temporal table with schema"""
        self.tables[table_name] = []
        self.schemas[table_name] = schema
            
    def insert(self, table_name: str, entity_id: str, data: Dict[str, Any]) -> TemporalRecord:
        """Insert new temporal record at current frame"""
        record = TemporalRecord(
            entity_id=entity_id,
            table_name=table_name,
            data=data.copy(),
            valid_from=self.current_frame,
            valid_to=None,
            transaction_frame=self.current_frame,
            operation='INSERT'
        )
        
        if table_name not in self.tables:
            self.tables[table_name] = []
            
        self.tables[table_name].append(record)
        return record
        
    def update(self, table_name: str, entity_id: str, new_data: Dict[str, Any]) -> TemporalRecord:
        """Update existing record (creates new version at current frame)"""
        # End validity of current record
        current_records = [r for r in self.tables[table_name] 
                          if r.entity_id == entity_id and r.valid_to is None]
        
        if current_records:
            current_record = current_records[0]
            current_record.valid_to = self.current_frame
            
            # Create new version
            updated_data = current_record.data.copy()
            updated_data.update(new_data)
            
            new_record = TemporalRecord(
                entity_id=entity_id,
                table_name=table_name,
                data=updated_data,
                valid_from=self.current_frame,
                valid_to=None,
                transaction_frame=self.current_frame,
                operation='UPDATE'
            )
            
            self.tables[table_name].append(new_record)
            return new_record
            
    def delete(self, table_name: str, entity_id: str):
        """Delete record (end its validity)"""
        current_records = [r for r in self.tables[table_name] 
                          if r.entity_id == entity_id and r.valid_to is None]
        
        for record in current_records:
            record.valid_to = self.current_frame
            
    def query_at_frame(self, table_name: str, frame: int) -> List[TemporalRecord]:
        """Get all records valid at specific frame"""
        if table_name not in self.tables:
            return []
            
        return [record for record in self.tables[table_name]
                if (record.valid_from <= frame and 
                    (record.valid_to is None or record.valid_to > frame) and
                    record.operation != 'DELETE')]
                    
    def query_history(self, table_name: str, entity_id: str) -> List[TemporalRecord]:
        """Get complete history of an entity across all frames"""
        if table_name not in self.tables:
            return []
        return [record for record in self.tables[table_name]
                if record.entity_id == entity_id]
                
    def temporal_aggregate(self, table_name: str, field: str, 
                         start_frame: int, end_frame: int) -> Dict[str, Any]:
        """Aggregate values across time range"""
        values = []
        
        for frame in range(start_frame, end_frame + 1):
            records = self.query_at_frame(table_name, frame)
            frame_values = [r.data.get(field, 0) for r in records if field in r.data and isinstance(r.data[field], (int, float))]
            values.extend(frame_values)
            
        return {
            'count': len(values),
            'sum': sum(values),
            'avg': sum(values) / len(values) if values else 0,
            'min': min(values) if values else 0,
            'max': max(values) if values else 0,
            'frames_analyzed': end_frame - start_frame + 1
        }
        
    def get_changes_between_frames(self, table_name: str, frame1: int, frame2: int):
        """Get all changes that occurred between two frames"""
        if table_name not in self.tables:
            return []
            
        changes = []
        for record in self.tables[table_name]:
            if frame1 <= record.transaction_frame <= frame2:
                changes.append({
                    'frame': record.transaction_frame,
                    'operation': record.operation,
                    'entity_id': record.entity_id,
                    'data': record.data,
                    'record': record
                })
                
        return sorted(changes, key=lambda x: x['frame'])
        
    def to_uvir_ops(self, query_type: str, frame: int, **kwargs) -> List[Dict[str, Any]]:
        """Convert query results to UVIR operations for visual display"""
        ops = []
        
        if query_type == 'table_state':
            table_name = kwargs.get('table_name')
            records = self.query_at_frame(table_name, frame)
            
            # Header
            ops.append({
                "op": "TEXT", "x": 20, "y": 20,
                "text": f"📊 {table_name.upper()} @ Frame {frame}",
                "color": "#FFFF00", "size": 18
            })
            
            ops.append({
                "op": "TEXT", "x": 20, "y": 45,
                "text": f"Active Records: {len(records)}",
                "color": "#00FF00", "size": 12
            })
            
            # Records as visual cards
            for i, record in enumerate(records[:12]):  # Max 12 visible records
                x = 50 + (i % 4) * 180
                y = 80 + (i // 4) * 80
                
                # Card background
                ops.append({
                    "op": "RECT", "x": x-5, "y": y-5, "w": 170, "h": 70,
                    "color": "#00AA00", "fill": False
                })
                
                # Entity ID
                ops.append({
                    "op": "TEXT", "x": x, "y": y,
                    "text": f"ID: {record.entity_id}",
                    "color": "#00FF00", "size": 12
                })
                
                # Data fields (first 3)
                data_items = list(record.data.items())[:3]
                for j, (key, value) in enumerate(data_items):
                    ops.append({
                        "op": "TEXT", "x": x, "y": y + 15 + j * 12,
                        "text": f"{key}: {str(value)[:15]}",
                        "color": "#AAAAAA", "size": 10
                    })
                    
        elif query_type == 'timeline':
            table_name = kwargs.get('table_name')
            entity_id = kwargs.get('entity_id')
            history = self.query_history(table_name, entity_id)
            
            ops.append({
                "op": "TEXT", "x": 20, "y": 20,
                "text": f"📈 Timeline: {entity_id} in {table_name}",
                "color": "#FFFF00", "size": 18
            })
            
            # Timeline visualization
            timeline_y = 100
            timeline_width = 700
            
            # Timeline base
            ops.append({
                "op": "RECT", "x": 50, "y": timeline_y, "w": timeline_width, "h": 2,
                "color": "#FFFFFF", "fill": True
            })
            
            # Plot history points
            for record in history:
                if record.transaction_frame <= self.max_frames:
                    x = 50 + (record.transaction_frame / self.max_frames) * timeline_width
                    color = {"INSERT": "#00FF00", "UPDATE": "#FFAA00", "DELETE": "#FF0000"}.get(record.operation, "#FFFFFF")
                    
                    ops.extend([
                        {"op": "RECT", "x": x-3, "y": timeline_y-8, "w": 6, "h": 16, "color": color, "fill": True},
                        {"op": "TEXT", "x": x-15, "y": timeline_y+20, "text": f"F{record.transaction_frame}", "color": color, "size": 8}
                    ])
                    
        elif query_type == 'aggregate':
            table_name = kwargs.get('table_name')
            field = kwargs.get('field')
            start_frame = kwargs.get('start_frame', 0)
            end_frame = kwargs.get('end_frame', frame)
            
            agg_result = self.temporal_aggregate(table_name, field, start_frame, end_frame)
            
            ops.append({
                "op": "TEXT", "x": 20, "y": 20,
                "text": f"📊 Temporal Aggregate: {field} ({start_frame}-{end_frame})",
                "color": "#FFFF00", "size": 18
            })
            
            # Display aggregate results as bars
            metrics = ['count', 'sum', 'avg', 'min', 'max']
            for i, metric in enumerate(metrics):
                value = agg_result[metric]
                x = 100 + i * 120
                y = 100
                bar_height = min(100, abs(value) if isinstance(value, (int, float)) else 10)
                
                ops.extend([
                    {"op": "RECT", "x": x, "y": y + 100 - bar_height, "w": 80, "h": bar_height, 
                     "color": "#0088FF", "fill": True},
                    {"op": "TEXT", "x": x, "y": y + 110, "text": metric.upper(), "color": "#FFFFFF", "size": 10},
                    {"op": "TEXT", "x": x, "y": y + 125, "text": str(round(value, 2)), "color": "#00FFFF", "size": 9}
                ])
                
        return ops
        
    def advance_frame(self):
        """Move to next frame"""
        self.current_frame = min(self.current_frame + 1, self.max_frames - 1)
        
    def set_frame(self, frame: int):
        """Jump to specific frame"""
        self.current_frame = max(0, min(frame, self.max_frames - 1))

    def get_database_stats(self):
        """Get current database statistics"""
        stats = {
            'current_frame': self.current_frame,
            'total_tables': len(self.tables),
            'total_records': sum(len(records) for records in self.tables.values()),
            'tables': {}
        }
        
        for table_name, records in self.tables.items():
            active_records = len(self.query_at_frame(table_name, self.current_frame))
            stats['tables'][table_name] = {
                'total_versions': len(records),
                'active_records': active_records,
                'schema': self.schemas.get(table_name, {})
            }
            
        return stats

def create_sample_temporal_database():
    """Create a sample temporal database with demo data"""
    db = TemporalDatabase()
    
    # Create tables
    db.create_table('employees', {
        'id': 'int', 'name': 'string', 'salary': 'int', 'department': 'string', 'age': 'int'
    })
    
    db.create_table('departments', {
        'id': 'int', 'name': 'string', 'budget': 'int', 'manager_id': 'int'
    })
    
    # Frame 0: Initial data
    db.insert('employees', 'emp1', {'id': 1, 'name': 'Alice', 'salary': 50000, 'department': 'Engineering', 'age': 25})
    db.insert('employees', 'emp2', {'id': 2, 'name': 'Bob', 'salary': 60000, 'department': 'Marketing', 'age': 30})
    db.insert('employees', 'emp3', {'id': 3, 'name': 'Charlie', 'salary': 55000, 'department': 'Engineering', 'age': 28})
    
    db.insert('departments', 'dept1', {'id': 1, 'name': 'Engineering', 'budget': 500000, 'manager_id': 1})
    db.insert('departments', 'dept2', {'id': 2, 'name': 'Marketing', 'budget': 200000, 'manager_id': 2})
    
    # Simulate temporal changes
    temporal_scenarios = [
        # Frame 5: Alice promotion
        (5, 'update', 'employees', 'emp1', {'salary': 65000}),
        
        # Frame 8: New hire
        (8, 'insert', 'employees', 'emp4', {'id': 4, 'name': 'Diana', 'salary': 48000, 'department': 'Marketing', 'age': 24}),
        
        # Frame 12: Budget increase
        (12, 'update', 'departments', 'dept1', {'budget': 600000}),
        
        # Frame 15: Department transfer
        (15, 'update', 'employees', 'emp2', {'department': 'Sales', 'salary': 58000}),
        
        # Frame 20: Departure
        (20, 'delete', 'employees', 'emp3'),
        
        # Frame 25: New department
        (25, 'insert', 'departments', 'dept3', {'id': 3, 'name': 'Research', 'budget': 400000, 'manager_id': 4}),
    ]
    
    for frame, action, table, entity_id, data in temporal_scenarios:
        db.set_frame(frame)
        
        if action == 'insert':
            db.insert(table, entity_id, data)
        elif action == 'update':
            db.update(table, entity_id, data)
        elif action == 'delete':
            db.delete(table, entity_id)
    
    # Reset to frame 0
    db.set_frame(0)
    return db

if __name__ == "__main__":
    # Demo usage
    db = create_sample_temporal_database()
    
    # Query at different frames
    print("Frame 0 employees:", len(db.query_at_frame('employees', 0)))
    print("Frame 10 employees:", len(db.query_at_frame('employees', 10)))  
    print("Frame 25 employees:", len(db.query_at_frame('employees', 25)))
    
    # Get history of Alice
    alice_history = db.query_history('employees', 'emp1')
    print(f"Alice has {len(alice_history)} versions")
    
    # Temporal aggregation
    salary_agg = db.temporal_aggregate('employees', 'salary', 0, 25)
    print("Salary aggregation:", salary_agg)