# Temporal Database Integration Guide

## Overview
This guide shows how to integrate the temporal database system with your existing UVIR bridge.

## 1. Update your existing server.py

Add these imports at the top of your server.py:

```python
from temporal_database_uvir import TemporalUVIRBridge
```

Then add this code after your existing FastAPI app creation:

```python
# Create temporal bridge
temporal_bridge = TemporalUVIRBridge()

# Add temporal endpoints to your FastAPI app
temporal_bridge.add_temporal_endpoints(app)
```

## 2. Complete Integration Example

Here's how your updated server.py should look with temporal database integrated:

```python
# Your existing imports...
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add temporal imports
from temporal_database_uvir import TemporalUVIRBridge

app = FastAPI(title="UVIR Bridge Server with Temporal Database")

# Your existing CORS and middleware setup...
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temporal bridge
temporal_bridge = TemporalUVIRBridge()

# Add temporal endpoints
temporal_bridge.add_temporal_endpoints(app)

# Your existing endpoints continue here...
@app.get("/")
async def root():
    return {"message": "UVIR Bridge with Temporal Database"}

# Your existing UVIR endpoints...
```

## 3. Frontend Integration

To use the temporal database in your frontend, you can either:

### Option A: Replace existing component
Replace your current component with TemporalDatabaseViewer:

```javascript
import TemporalDatabaseViewer from './TemporalDatabaseViewer';

function App() {
    return <TemporalDatabaseViewer />;
}
```

### Option B: Add as new route/tab
Add temporal database as a new section in your existing app:

```javascript
import { useState } from 'react';
import TemporalDatabaseViewer from './TemporalDatabaseViewer';
import YourExistingComponent from './YourExistingComponent';

function App() {
    const [activeTab, setActiveTab] = useState('uvir');
    
    return (
        <div>
            <nav>
                <button onClick={() => setActiveTab('uvir')}>UVIR Bridge</button>
                <button onClick={() => setActiveTab('temporal')}>Temporal Database</button>
            </nav>
            
            {activeTab === 'uvir' && <YourExistingComponent />}
            {activeTab === 'temporal' && <TemporalDatabaseViewer />}
        </div>
    );
}
```

## 4. Testing the Integration

### Start the server:
```bash
cd your-project-directory
python server.py
```

### Test temporal endpoints:
```bash
# Get database stats
curl http://localhost:8844/temporal/stats

# Query employees at frame 0
curl http://localhost:8844/temporal/query/employees?frame=0

# Time travel to frame 10
curl -X POST http://localhost:8844/temporal/time_travel \
  -H "Content-Type: application/json" \
  -d '{"frame": 10}'

# Execute temporal SQL
curl -X POST http://localhost:8844/temporal/sql \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM employees AS OF FRAME 5"}'
```

## 5. Example Usage Scenarios

### Scenario 1: Time Travel Queries
```javascript
// Time travel to see data at frame 10
const result = await fetch('http://localhost:8844/temporal/time_travel', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({frame: 10})
});

const data = await result.json();
// data.ops contains UVIR operations to render the database state at frame 10
```

### Scenario 2: Entity History
```javascript
// Get complete history of employee 'emp1'
const history = await fetch('http://localhost:8844/temporal/history/employees/emp1');
const data = await history.json();
// data.ops contains timeline visualization
```

### Scenario 3: Live Scenario
```javascript
// Watch database evolve in real-time
const eventSource = new EventSource('http://localhost:8844/temporal/scenario');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'ir') {
        // Render data.ops to show evolving database state
        renderUVIROps(data.ops);
    }
};
```

## 6. Customization Options

### Adding Custom Tables
```python
# In temporal_database_uvir.py, modify create_sample_temporal_database():

def create_sample_temporal_database():
    db = TemporalDatabase()
    
    # Add your custom tables
    db.create_table('products', {
        'id': 'int', 'name': 'string', 'price': 'float', 'category': 'string'
    })
    
    db.create_table('orders', {
        'id': 'int', 'customer_id': 'int', 'product_id': 'int', 'quantity': 'int', 'total': 'float'
    })
    
    # Add initial data
    db.insert('products', 'prod1', {'id': 1, 'name': 'Laptop', 'price': 999.99, 'category': 'Electronics'})
    
    return db
```

### Custom Temporal Scenarios
```python
# Add custom scenarios to the scenario endpoint:
scenarios = [
    {"frame": 3, "action": "insert", "table": "products", "id": "prod2", 
     "data": {"id": 2, "name": "Mouse", "price": 29.99, "category": "Electronics"}, 
     "desc": "New product added"},
    
    {"frame": 7, "action": "update", "table": "products", "id": "prod1", 
     "data": {"price": 899.99}, "desc": "Price reduction"},
]
```

### Custom UVIR Visualizations
```python
# In temporal_database.py, modify to_uvir_ops() for custom visualizations:

def to_uvir_ops(self, query_type: str, frame: int, **kwargs):
    ops = []
    
    if query_type == 'custom_chart':
        # Add your custom visualization logic
        ops.append({
            "op": "BAR",
            "x": 100, "y": 100, "len": 200,
            "label": "Custom Metric",
            "color": "#FF6600"
        })
    
    return ops
```

## 7. Advanced Features

### Bitemporal Support
The system supports both transaction time (when the change was made) and valid time (when the change applies to reality).

### Temporal Joins
Join tables at specific points in time to see relationships as they existed.

### Event Sourcing
Every change is captured and can be replayed to reconstruct any historical state.

### Visual Query Results
All query results are immediately converted to UVIR operations for visual display.

## 8. Performance Considerations

- The system is optimized for visualization and exploration, not high-volume production use
- For large datasets, consider pagination in the UVIR visualization
- Frame-based storage scales well up to thousands of frames
- Indexes can be added for frequently queried fields

## 9. Next Steps

After integration, you can:
1. Add more complex temporal queries
2. Implement temporal triggers
3. Add distributed temporal consistency
4. Create temporal views
5. Build temporal analytics dashboards

This temporal database system transforms your UVIR bridge into a full-featured time-travel database with visual query capabilities!