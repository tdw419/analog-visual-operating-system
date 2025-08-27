"""
Infinite Visual Computer Comprehensive Demo
Showcases all paradigms: Analog, Memory, Filesystem, Database across infinite space
"""

import time
import json
import numpy as np
from infinite_visual_computer import InfiniteVisualComputer, ChunkCoordinate

def demo_performance_test():
    """Test performance with large-scale operations"""
    print("\n=== PERFORMANCE TEST ===")
    
    computer = InfiniteVisualComputer(chunk_size=32, max_loaded_chunks=200)
    
    # Test 1: Massive pixel setting across many chunks
    start_time = time.time()
    pixels_set = 0
    
    for chunk_x in range(-5, 6):  # 11x11 chunks = 121 chunks
        for chunk_y in range(-5, 6):
            base_world_x = chunk_x * 32
            base_world_y = chunk_y * 32
            
            # Set diagonal pattern in each chunk
            for i in range(32):
                computer.set_world_pixel(base_world_x + i, base_world_y + i, (255, 0, 0, 255))
                pixels_set += 1
    
    pixel_time = time.time() - start_time
    print(f"Set {pixels_set} pixels across {len(computer.loaded_chunks)} chunks in {pixel_time:.3f}s")
    print(f"Rate: {pixels_set/pixel_time:.0f} pixels/second")
    
    # Test 2: Cross-chunk cellular automata performance
    start_time = time.time()
    for frame in range(10):
        computer.advance_frame()
    ca_time = time.time() - start_time
    
    print(f"Computed 10 cellular automata frames in {ca_time:.3f}s")
    print(f"Rate: {10/ca_time:.1f} frames/second")
    
    stats = computer.get_statistics()
    print(f"Final state: {stats}")
    
    return computer

def demo_cross_chunk_patterns():
    """Demonstrate patterns that span multiple chunks"""
    print("\n=== CROSS-CHUNK PATTERNS ===")
    
    computer = InfiniteVisualComputer(chunk_size=16, max_loaded_chunks=50)
    
    # Create a large spiral pattern across chunks
    center_x, center_y = 0, 0
    radius = 50  # Spans multiple 16x16 chunks
    
    for angle in range(0, 360, 5):
        rad = np.radians(angle)
        x = int(center_x + radius * np.cos(rad))
        y = int(center_y + radius * np.sin(rad))
        
        # Color based on angle
        hue = angle
        r = int(255 * (1 + np.sin(np.radians(hue))) / 2)
        g = int(255 * (1 + np.sin(np.radians(hue + 120))) / 2)
        b = int(255 * (1 + np.sin(np.radians(hue + 240))) / 2)
        
        computer.set_world_pixel(x, y, (r, g, b, 255))
    
    print(f"Created spiral pattern across {len(computer.loaded_chunks)} chunks")
    
    # Test cross-chunk computation
    print("Running cross-chunk cellular automata...")
    for frame in range(5):
        computer.advance_frame()
        stats = computer.get_statistics()
        print(f"Frame {frame + 1}: {stats['active_chunks']} active chunks")
    
    # Verify pattern integrity across chunks
    view = computer.get_view_window(0, 0, 100, 100)
    active_pixels = np.sum(np.sum(view[:,:,:3], axis=2) > 0)
    print(f"Pattern integrity: {active_pixels} active pixels in central view")
    
    return computer

def demo_multi_paradigm_integration():
    """Demonstrate all four paradigms working together"""
    print("\n=== MULTI-PARADIGM INTEGRATION ===")
    
    computer = InfiniteVisualComputer(chunk_size=32, max_loaded_chunks=100)
    
    # Set up demonstration regions
    regions = {
        'analog': (0, 0),       # Origin: Analog screen computer
        'memory': (200, 0),     # Right: Visual memory
        'filesystem': (0, 200), # Down: Frame filesystem  
        'database': (200, 200)  # Diagonal: Temporal database
    }
    
    print("Setting up paradigm demonstration regions...")
    
    # 1. Analog Screen Computer - Conway's Life patterns
    glider_pattern = [(1,0), (2,1), (0,2), (1,2), (2,2)]
    for dx, dy in glider_pattern:
        computer.set_world_pixel(regions['analog'][0] + dx, regions['analog'][1] + dy, 
                                (0, 255, 0, 255))
    
    # 2. Visual Memory - Store configuration data
    config_data = {
        'system_version': '1.0.0',
        'chunk_size': 32,
        'paradigms': ['analog', 'memory', 'filesystem', 'database']
    }
    
    memory_x, memory_y = regions['memory']
    computer.visual_memory_write(memory_x, memory_y, config_data, 'spatial')
    computer.visual_memory_write(memory_x + 10, memory_y, 0xFF00FF, 'color')
    
    # 3. Frame Filesystem - Store historical data across frames
    fs_x, fs_y = regions['filesystem']
    for frame in range(3):
        file_data = {
            'frame': frame,
            'timestamp': time.time(),
            'data': f"Frame {frame} historical record",
            'checksum': hash(f"frame_{frame}") & 0xFFFF
        }
        computer.frame_filesystem_write(fs_x, fs_y, frame, file_data)
    
    # 4. Temporal Database - Insert records with coordinates
    db_x, db_y = regions['database']
    entities = [
        ('region_1', {'name': 'Alpha Base', 'population': 1500}),
        ('region_2', {'name': 'Beta Station', 'population': 2300}),
        ('region_3', {'name': 'Gamma Outpost', 'population': 800})
    ]
    
    for i, (entity_id, data) in enumerate(entities):
        computer.temporal_database_insert(
            db_x + i * 10, db_y + i * 5, 
            'settlements', entity_id, data
        )
    
    print("All paradigms initialized. Running integrated simulation...")
    
    # Run integrated simulation
    for frame in range(10):
        print(f"\n--- Frame {frame + 1} ---")
        
        # Advance frame (triggers all computations)
        computer.advance_frame()
        
        # Test memory retrieval
        if frame == 5:
            memory_result = computer.visual_memory_read(memory_x, memory_y)
            print(f"Memory read: {memory_result['data'] if memory_result else 'None'}")
        
        # Test filesystem retrieval  
        if frame == 7:
            fs_result = computer.frame_filesystem_read(fs_x, fs_y, 1)
            print(f"Filesystem read (frame 1): {fs_result['data'] if fs_result else 'None'}")
        
        # Test database query
        if frame == 9:
            db_results = computer.temporal_database_query(
                (db_x - 5, db_y - 5, db_x + 35, db_y + 20),
                'settlements', frame
            )
            print(f"Database query: {len(db_results)} settlements found")
            for result in db_results:
                print(f"  - {result['data']['name']}: {result['data']['population']} people")
        
        stats = computer.get_statistics()
        print(f"Stats: {stats['loaded_chunks']} chunks, {stats['active_chunks']} active")
    
    # Final state analysis
    print(f"\n--- Final Analysis ---")
    final_stats = computer.get_statistics()
    print(f"Final statistics: {json.dumps(final_stats, indent=2)}")
    
    # Test view windows of each region
    for name, (x, y) in regions.items():
        view = computer.get_view_window(x, y, 32, 32)
        active_pixels = np.sum(np.sum(view[:,:,:3], axis=2) > 0)
        print(f"{name.title()} region: {active_pixels} active pixels")
    
    return computer

def demo_memory_management():
    """Test chunk loading/unloading and memory management"""
    print("\n=== MEMORY MANAGEMENT TEST ===")
    
    computer = InfiniteVisualComputer(chunk_size=16, max_loaded_chunks=20)
    
    # Phase 1: Load many chunks
    print("Phase 1: Loading chunks across large area...")
    chunk_coords = []
    for x in range(-10, 11):  # 21x21 = 441 chunks total
        for y in range(-10, 11):
            world_x = x * 16 + 8  # Center of each chunk
            world_y = y * 16 + 8
            computer.set_world_pixel(world_x, world_y, (128, 128, 128, 255))
            chunk_coords.append((x, y))
            
            if len(chunk_coords) % 50 == 0:
                stats = computer.get_statistics()
                print(f"  Processed {len(chunk_coords)} chunks, "
                      f"{stats['loaded_chunks']} in memory, "
                      f"{stats['stored_chunks']} in storage")
    
    print(f"Attempted to access {len(chunk_coords)} chunks")
    
    # Phase 2: Test memory management during computation
    print("\nPhase 2: Running computation to trigger memory management...")
    for frame in range(20):
        computer.advance_frame()
        
        if frame % 5 == 0:
            stats = computer.get_statistics()
            print(f"  Frame {frame}: {stats['loaded_chunks']} loaded, "
                  f"{stats['stored_chunks']} stored, "
                  f"{stats['active_chunks']} active")
    
    # Phase 3: Access distant chunks to test reloading
    print("\nPhase 3: Testing chunk reloading...")
    test_coords = [(-200, -200), (300, 150), (-150, 250)]
    
    for i, (x, y) in enumerate(test_coords):
        pixel = computer.get_world_pixel(x, y)
        computer.set_world_pixel(x, y, (255, i * 85, 255 - i * 85, 255))
        print(f"  Accessed distant chunk at ({x}, {y})")
        
        stats = computer.get_statistics()
        print(f"    Memory state: {stats['loaded_chunks']} loaded chunks")
    
    final_stats = computer.get_statistics()
    print(f"\nFinal memory state: {json.dumps(final_stats, indent=2)}")
    
    return computer

def demo_temporal_queries():
    """Demonstrate complex temporal database queries"""
    print("\n=== TEMPORAL QUERIES DEMO ===")
    
    computer = InfiniteVisualComputer(chunk_size=32, max_loaded_chunks=50)
    
    # Create a temporal story across frames
    story_events = [
        (0, 'settlements', 'town_alpha', {'name': 'Alpha Town', 'population': 1000, 'status': 'founded'}),
        (2, 'settlements', 'town_beta', {'name': 'Beta City', 'population': 1500, 'status': 'founded'}),
        (5, 'settlements', 'town_alpha', {'name': 'Alpha Town', 'population': 1200, 'status': 'growing'}),
        (7, 'settlements', 'town_gamma', {'name': 'Gamma Village', 'population': 500, 'status': 'founded'}),
        (10, 'settlements', 'town_beta', {'name': 'Beta City', 'population': 2000, 'status': 'thriving'}),
        (12, 'settlements', 'town_alpha', {'name': 'Alpha Town', 'population': 800, 'status': 'declining'}),
        (15, 'settlements', 'town_delta', {'name': 'Delta Outpost', 'population': 300, 'status': 'founded'}),
    ]
    
    # Execute story events
    for frame, table, entity_id, data in story_events:
        # Advance to target frame
        while computer.current_frame < frame:
            computer.advance_frame()
        
        # Insert record at specific coordinates (spread them out)
        x = (hash(entity_id) % 200) - 100
        y = (hash(entity_id) % 200) - 100
        computer.temporal_database_insert(x, y, table, entity_id, data)
        
        print(f"Frame {frame}: {data['status']} - {data['name']} "
              f"(pop: {data['population']}) at ({x}, {y})")
    
    # Advance to final frame
    while computer.current_frame < 20:
        computer.advance_frame()
    
    print(f"\nStory complete at frame {computer.current_frame}")
    
    # Run temporal queries
    print("\n--- Temporal Queries ---")
    
    # Query 1: All settlements at different time points
    for query_frame in [0, 5, 10, 15, 20]:
        results = computer.temporal_database_query(
            (-150, -150, 150, 150), 'settlements', query_frame
        )
        print(f"\nFrame {query_frame}: {len(results)} settlements")
        for result in results:
            data = result['data']
            coords = result['world_coords']
            print(f"  - {data['name']}: {data['population']} people, {data['status']} at {coords}")
    
    # Query 2: Track specific settlement over time
    print(f"\n--- Alpha Town Timeline ---")
    alpha_history = []
    for query_frame in range(21):
        results = computer.temporal_database_query(
            (-150, -150, 150, 150), 'settlements', query_frame
        )
        alpha_records = [r for r in results if r['entity_id'] == 'town_alpha']
        if alpha_records:
            record = alpha_records[0]
            alpha_history.append((query_frame, record['data']['population'], record['data']['status']))
    
    for frame, pop, status in alpha_history:
        print(f"  Frame {frame}: {pop} people, {status}")
    
    # Query 3: Population analysis
    print(f"\n--- Population Analysis ---")
    frame_populations = {}
    for query_frame in [0, 5, 10, 15, 20]:
        results = computer.temporal_database_query(
            (-150, -150, 150, 150), 'settlements', query_frame
        )
        total_pop = sum(r['data']['population'] for r in results)
        frame_populations[query_frame] = total_pop
        print(f"Frame {query_frame}: Total population = {total_pop}")
    
    return computer

def run_all_demos():
    """Run all demonstration scenarios"""
    print("🌌 INFINITE VISUAL COMPUTER - COMPREHENSIVE DEMO")
    print("=" * 60)
    
    demos = [
        ("Multi-Paradigm Integration", demo_multi_paradigm_integration),
        ("Cross-Chunk Patterns", demo_cross_chunk_patterns),
        ("Performance Test", demo_performance_test),
        ("Memory Management", demo_memory_management),
        ("Temporal Queries", demo_temporal_queries),
    ]
    
    results = {}
    
    for name, demo_func in demos:
        print(f"\n🚀 Starting: {name}")
        print("-" * 40)
        
        start_time = time.time()
        try:
            computer = demo_func()
            duration = time.time() - start_time
            stats = computer.get_statistics()
            
            results[name] = {
                'success': True,
                'duration': duration,
                'final_stats': stats
            }
            
            print(f"✅ {name} completed in {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            results[name] = {
                'success': False,
                'duration': duration,
                'error': str(e)
            }
            print(f"❌ {name} failed after {duration:.2f}s: {e}")
    
    # Summary
    print(f"\n📊 DEMO SUMMARY")
    print("=" * 60)
    
    total_time = sum(r['duration'] for r in results.values())
    successful = sum(1 for r in results.values() if r['success'])
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Success rate: {successful}/{len(demos)} demos")
    
    for name, result in results.items():
        status = "✅" if result['success'] else "❌"
        print(f"{status} {name}: {result['duration']:.2f}s")
        
        if result['success'] and 'final_stats' in result:
            stats = result['final_stats']
            print(f"    Final state: {stats['loaded_chunks']} chunks, "
                  f"frame {stats['current_frame']}")
    
    print(f"\n🎉 Infinite Visual Computer demo complete!")
    return results

if __name__ == "__main__":
    results = run_all_demos()