#!/usr/bin/env python3
"""
Comparison Test: IDS Capture vs Semantic Conversion

This script demonstrates the key differences between:
1. Option A: Capturing running programs to CSV (pixel-level)
2. Option B: Converting source code to CSV (semantic-level)

Run this to see the trade-offs in action.
"""

import subprocess
import sys
import tempfile
import csv
from pathlib import Path


def run_transpiler_demo():
    """Run the semantic transpiler on the demo script"""
    print("🔄 Running semantic transpiler (Option B)...")
    
    demo_script = Path("examples/transpiler_demo.py")
    output_csv = Path("output/semantic_demo.csv")
    output_csv.parent.mkdir(exist_ok=True)
    
    result = subprocess.run([
        sys.executable, "py_to_csv_transpiler.py",
        "--src", str(demo_script),
        "--out", str(output_csv),
        "--verbose"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Semantic transpilation successful")
        analyze_csv(output_csv, "Semantic (Option B)")
    else:
        print(f"❌ Transpilation failed: {result.stderr}")
    
    return output_csv


def run_capture_simulation():
    """Simulate what an IDS capture would look like"""
    print("\n🔄 Simulating IDS capture (Option A)...")
    
    # Create a simulated "pixel capture" CSV
    # This would be much larger in reality, with many RECT operations per frame
    output_csv = Path("output/capture_demo.csv")
    output_csv.parent.mkdir(exist_ok=True)
    
    operations = []
    
    # Simulate capturing a program that draws rectangles
    # In reality, this would be hundreds of small RECT ops from screen diffing
    for frame in range(4):
        # Background "tiles" (many small rects from screen diffing)
        for y in range(0, 400, 8):  # 8x8 pixel tiles
            for x in range(0, 600, 8):
                if (x + y + frame) % 3 == 0:  # Simulate some change detection
                    operations.append({
                        'frame': frame,
                        'time': 0.0,
                        'op': 'RECT',
                        'x': x, 'y': y, 'w': 8, 'h': 8,
                        'r': 0, 'g': 20, 'b': 40,
                        'intensity': 1.0,
                        'text': '', 'id': ''
                    })
        
        # Main content rectangle (inferred from larger pixel regions)
        operations.append({
            'frame': frame,
            'time': 0.0,
            'op': 'RECT',
            'x': 100 + frame * 30, 'y': 50, 'w': 60, 'h': 40,
            'r': 255 - frame * 50, 'g': 100 + frame * 50, 'b': 200,
            'intensity': 1.0,
            'text': '', 'id': ''
        })
        
        # Text (possibly inferred from font atlas, or just more small rects)
        operations.append({
            'frame': frame,
            'time': 0.0,
            'op': 'TEXT',
            'x': 105 + frame * 30, 'y': 65,
            'w': '', 'h': '',
            'r': 255, 'g': 255, 'b': 255,
            'intensity': 1.0,
            'text': f'Frame {frame}', 'id': ''
        })
        
        operations.append({
            'frame': frame,
            'time': 0.016,
            'op': 'COMMIT',
            'x': '', 'y': '', 'w': '', 'h': '',
            'r': '', 'g': '', 'b': '',
            'intensity': '', 'text': '', 'id': ''
        })
    
    # Write simulated capture CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'frame', 'time', 'op', 'x', 'y', 'w', 'h',
            'r', 'g', 'b', 'intensity', 'text', 'id'
        ])
        writer.writeheader()
        writer.writerows(operations)
    
    print("✅ IDS capture simulation complete")
    analyze_csv(output_csv, "IDS Capture (Option A)")
    
    return output_csv


def analyze_csv(csv_path, label):
    """Analyze a CSV file and show key metrics"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        operations = list(reader)
    
    # Count operation types
    op_counts = {}
    frame_count = 0
    text_ops = []
    
    for op in operations:
        op_type = op['op']
        op_counts[op_type] = op_counts.get(op_type, 0) + 1
        
        if op_type == 'COMMIT':
            frame_count += 1
        elif op_type == 'TEXT' and op['text']:
            text_ops.append(op['text'])
    
    file_size = csv_path.stat().st_size
    
    print(f"\n📊 Analysis: {label}")
    print(f"   File size: {file_size:,} bytes")
    print(f"   Total operations: {len(operations):,}")
    print(f"   Frames: {frame_count}")
    print(f"   Operations per frame: {len(operations) // max(1, frame_count):.1f}")
    print(f"   Operation types: {dict(op_counts)}")
    
    if text_ops:
        print(f"   Text content: {text_ops[:3]}{'...' if len(text_ops) > 3 else ''}")


def compare_approaches():
    """Compare the two approaches side by side"""
    print("🎯 VisualPython: IDS Capture vs Semantic Conversion Comparison")
    print("=" * 70)
    
    # Run both approaches
    semantic_csv = run_transpiler_demo()
    capture_csv = run_capture_simulation()
    
    print("\n" + "=" * 70)
    print("📈 COMPARISON SUMMARY")
    print("=" * 70)
    
    semantic_size = semantic_csv.stat().st_size
    capture_size = capture_csv.stat().st_size
    
    print(f"Semantic Conversion (Option B):")
    print(f"  ✅ Compact: {semantic_size:,} bytes")
    print(f"  ✅ High fidelity: Preserves program logic and intent")
    print(f"  ✅ Efficient: Few operations per frame")
    print(f"  ❌ Narrow scope: Only works for supported languages")
    print(f"  ❌ Development effort: Requires transpiler for each language")
    
    print(f"\nIDS Capture (Option A):")
    print(f"  ❌ Large: {capture_size:,} bytes ({capture_size/semantic_size:.1f}x larger)")
    print(f"  ❌ Low fidelity: Only captures visual output")
    print(f"  ❌ Inefficient: Many operations from pixel diffing")
    print(f"  ✅ Universal: Works with any program")
    print(f"  ✅ Quick implementation: No language-specific work needed")
    
    efficiency_ratio = capture_size / semantic_size
    print(f"\n🎯 RECOMMENDATION:")
    if efficiency_ratio > 5:
        print(f"   Start with Option B (Semantic Conversion)")
        print(f"   The {efficiency_ratio:.1f}x efficiency gain and semantic fidelity")
        print(f"   make it the better foundation for true analog computing.")
    else:
        print(f"   Consider hybrid approach")
    
    print(f"\n🔄 Test the semantic output:")
    print(f"   python visualpython_unified.py csv play {semantic_csv} --backend sim")


if __name__ == '__main__':
    compare_approaches()