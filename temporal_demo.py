#!/usr/bin/env python3
"""
Temporal Database Demo Script
Demonstrates the revolutionary frame-based temporal database system
"""

import asyncio
import json
from temporal_database import TemporalDatabase, create_sample_temporal_database

def demo_basic_temporal_operations():
    """Demo 1: Basic temporal operations"""
    print("🕰️  DEMO 1: Basic Temporal Operations")
    print("=" * 50)
    
    db = TemporalDatabase(max_frames=10)
    
    # Create table
    db.create_table('users', {'id': 'int', 'name': 'string', 'age': 'int', 'status': 'string'})
    
    # Frame 0: Initial data
    print("Frame 0: Creating initial user")
    db.insert('users', 'user1', {'id': 1, 'name': 'Alice', 'age': 25, 'status': 'active'})
    users_f0 = db.query_at_frame('users', 0)
    print(f"  Users at frame 0: {len(users_f0)} - {users_f0[0].data}")
    
    # Frame 3: Update user
    db.set_frame(3)
    print("Frame 3: Updating user age")
    db.update('users', 'user1', {'age': 26})
    users_f3 = db.query_at_frame('users', 3)
    print(f"  Users at frame 3: {len(users_f3)} - {users_f3[0].data}")
    
    # Frame 5: Change status
    db.set_frame(5)
    print("Frame 5: Changing user status")
    db.update('users', 'user1', {'status': 'inactive'})
    users_f5 = db.query_at_frame('users', 5)
    print(f"  Users at frame 5: {len(users_f5)} - {users_f5[0].data}")
    
    # Time travel back to frame 0
    print("\n🔄 Time Travel Demonstration:")
    users_back_to_0 = db.query_at_frame('users', 0)
    print(f"  Back to frame 0: {users_back_to_0[0].data}")
    print(f"  At frame 3: {db.query_at_frame('users', 3)[0].data}")
    print(f"  At frame 5: {db.query_at_frame('users', 5)[0].data}")
    
    # Show complete history
    print("\n📜 Complete History:")
    history = db.query_history('users', 'user1')
    for record in history:
        print(f"  Frame {record.transaction_frame}: {record.operation} -> {record.data}")
    
    print("\n")

def demo_temporal_scenarios():
    """Demo 2: Complex temporal scenarios"""
    print("🎬 DEMO 2: Complex Temporal Scenarios")
    print("=" * 50)
    
    db = create_sample_temporal_database()
    
    scenarios = [
        (0, "Initial state - 3 employees, 2 departments"),
        (5, "Alice promotion - salary increase"),
        (8, "New hire - Diana joins Marketing"),
        (12, "Budget expansion - Engineering gets more funding"),
        (15, "Department transfer - Bob moves to Sales"),
        (20, "Employee departure - Charlie leaves"),
        (25, "Company growth - New Research department")
    ]
    
    for frame, description in scenarios:
        employees = db.query_at_frame('employees', frame)
        departments = db.query_at_frame('departments', frame)
        
        print(f"Frame {frame:2d}: {description}")
        print(f"         Employees: {len(employees)}, Departments: {len(departments)}")
        
        if employees:
            total_salary = sum(emp.data.get('salary', 0) for emp in employees)
            avg_salary = total_salary / len(employees)
            print(f"         Total Payroll: ${total_salary:,}, Avg Salary: ${avg_salary:,.0f}")
        
        print()

def demo_temporal_analytics():
    """Demo 3: Temporal analytics and aggregations"""
    print("📊 DEMO 3: Temporal Analytics")
    print("=" * 50)
    
    db = create_sample_temporal_database()
    
    # Salary trends over time
    print("💰 Salary Analysis Across Time:")
    for frame in [0, 10, 20, 30]:
        agg = db.temporal_aggregate('employees', 'salary', frame, frame)
        employees = db.query_at_frame('employees', frame)
        print(f"Frame {frame:2d}: {agg['count']} employees, Total: ${agg['sum']:,}, Avg: ${agg['avg']:,.0f}")
    
    # Growth analysis
    print("\n📈 Growth Analysis (Frames 0-25):")
    growth_agg = db.temporal_aggregate('employees', 'salary', 0, 25)
    print(f"  Total person-frames analyzed: {growth_agg['frames_analyzed']}")
    print(f"  Salary sum across all frames: ${growth_agg['sum']:,}")
    print(f"  Average salary across time: ${growth_agg['avg']:,.0f}")
    print(f"  Min salary recorded: ${growth_agg['min']:,}")
    print(f"  Max salary recorded: ${growth_agg['max']:,}")
    
    # Change frequency analysis
    print("\n🔄 Change Frequency Analysis:")
    changes = db.get_changes_between_frames('employees', 0, 25)
    operations = {}
    for change in changes:
        op = change['operation']
        operations[op] = operations.get(op, 0) + 1
    
    print(f"  Total changes: {len(changes)}")
    for op, count in operations.items():
        print(f"  {op}: {count}")

def demo_bitemporal_features():
    """Demo 4: Bitemporal features (transaction time vs valid time)"""
    print("⏰ DEMO 4: Bitemporal Features")  
    print("=" * 50)
    
    db = TemporalDatabase(max_frames=15)
    db.create_table('contracts', {
        'id': 'int', 'client': 'string', 'value': 'int', 'start_date': 'string', 'end_date': 'string'
    })
    
    # Frame 5: Contract created (transaction time = 5, valid from frame 3)
    db.set_frame(5)
    contract = db.insert('contracts', 'contract1', {
        'id': 1, 'client': 'ACME Corp', 'value': 100000, 
        'start_date': '2024-01-01', 'end_date': '2024-12-31'
    })
    # Manually set valid_from to simulate contract starting earlier
    contract.valid_from = 3
    
    print("Contract created at frame 5, but valid from frame 3")
    print(f"Transaction time: {contract.transaction_frame}")
    print(f"Valid from: {contract.valid_from}")
    
    # Frame 8: Contract updated (correcting earlier mistake)
    db.set_frame(8)  
    db.update('contracts', 'contract1', {'value': 120000})
    
    print("\nContract value corrected at frame 8")
    
    # Show bitemporal queries
    print("\nBitemporal Query Results:")
    print("Frame 2 (before valid time): ", len(db.query_at_frame('contracts', 2)), "contracts")
    print("Frame 4 (during valid time, before transaction): ", len(db.query_at_frame('contracts', 4)), "contracts") 
    print("Frame 6 (after transaction): ", db.query_at_frame('contracts', 6)[0].data['value'] if db.query_at_frame('contracts', 6) else "No data")
    print("Frame 9 (after update): ", db.query_at_frame('contracts', 9)[0].data['value'] if db.query_at_frame('contracts', 9) else "No data")

def demo_visual_queries():
    """Demo 5: Visual query generation"""
    print("🎨 DEMO 5: Visual Query Generation")
    print("=" * 50)
    
    db = create_sample_temporal_database()
    
    # Generate UVIR operations for different query types
    print("Generating UVIR operations for visual display...")
    
    # Table state visualization
    table_ops = db.to_uvir_ops('table_state', 15, table_name='employees')
    print(f"\nTable state visualization: {len(table_ops)} UVIR operations")
    print("Sample operations:")
    for op in table_ops[:3]:
        print(f"  {op}")
    
    # Timeline visualization
    timeline_ops = db.to_uvir_ops('timeline', 15, table_name='employees', entity_id='emp1')
    print(f"\nTimeline visualization: {len(timeline_ops)} UVIR operations")
    
    # Aggregate visualization
    agg_ops = db.to_uvir_ops('aggregate', 15, table_name='employees', field='salary', start_frame=0, end_frame=15)
    print(f"\nAggregate visualization: {len(agg_ops)} UVIR operations")

def demo_performance_characteristics():
    """Demo 6: Performance characteristics"""
    print("⚡ DEMO 6: Performance Characteristics")
    print("=" * 50)
    
    import time
    
    db = TemporalDatabase(max_frames=100)
    db.create_table('performance_test', {'id': 'int', 'value': 'int'})
    
    # Insert performance test
    start_time = time.time()
    for frame in range(50):
        db.set_frame(frame)
        for i in range(10):  # 10 records per frame
            db.insert('performance_test', f'record_{frame}_{i}', {'id': frame*10+i, 'value': frame*100+i})
    
    insert_time = time.time() - start_time
    print(f"Inserted 500 records across 50 frames in {insert_time:.3f} seconds")
    
    # Query performance test
    start_time = time.time()
    for frame in range(0, 50, 5):  # Query every 5th frame
        records = db.query_at_frame('performance_test', frame)
    
    query_time = time.time() - start_time
    print(f"Queried 10 different frames in {query_time:.3f} seconds")
    
    # Memory usage
    total_records = sum(len(records) for records in db.tables.values())
    print(f"Total records in memory: {total_records}")
    print(f"Memory efficiency: ~{total_records/500:.1f}x records (due to versioning)")

def main():
    """Run all demos"""
    print("🚀 TEMPORAL DATABASE DEMONSTRATION")
    print("=" * 60)
    print("Revolutionary frame-based temporal database system")
    print("Each frame = database snapshot | Time = primary dimension")
    print("=" * 60)
    print()
    
    try:
        demo_basic_temporal_operations()
        demo_temporal_scenarios()
        demo_temporal_analytics()
        demo_bitemporal_features()
        demo_visual_queries()
        demo_performance_characteristics()
        
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("\nKey Features Demonstrated:")
        print("• ⏰ Time travel queries - access any historical state")
        print("• 📊 Temporal analytics - aggregate across time dimensions")
        print("• 🔄 Event sourcing - complete change history")
        print("• 🎨 Visual queries - automatic UVIR operation generation")
        print("• ⚡ Bitemporal support - transaction vs valid time")
        print("• 📈 Performance scaling - efficient frame-based storage")
        
        print(f"\n🎯 Ready for integration with UVIR Bridge!")
        print("Next steps: Run 'python server.py' to start the temporal database server")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()