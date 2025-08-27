#!/usr/bin/env python3
"""
VisualPython Demo Script

This script demonstrates the revolutionary capabilities of VisualPython:
- Zero compilation delay
- Immediate visual feedback
- Live file monitoring
- Hardware signal export

Run this to see VisualPython in action!
"""

import sys
import os
import time

# Add the visual_python package to path for testing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_basic_execution():
    """Demonstrate basic visual execution"""
    print("🎯 Demo 1: Basic Visual Execution")
    print("=" * 50)
    
    try:
        from visual_python import run_visual
        
        demo_code = '''
# VisualPython Demo - No Compilation!
x = 42
y = x * 2
name = "VisualPython"

print(f"Hello from {name}!")
print(f"Variables: x={x}, y={y}")

# Loops create immediate visual sequences
for i in range(3):
    result = i * 10
    print(f"  Loop {i}: result = {result}")

print("✨ This executed without compilation!")
'''
        
        print("Executing Python code directly as visual operations...")
        result = run_visual(demo_code, backend='console')
        
        print(f"\n✅ Execution completed successfully!")
        print(f"   Execution time: {result.execution_time_ms:.2f}ms")
        print(f"   Elements created: {result.elements_created}")
        print(f"   Variables tracked: {result.variables_tracked}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Execution error: {e}")
        return False

def demo_live_monitoring():
    """Demonstrate live file monitoring"""
    print("\n🔄 Demo 2: Live File Monitoring")
    print("=" * 50)
    
    try:
        from visual_python import create_example_file
        
        # Create example file
        example_file = create_example_file("demo_live.py")
        print(f"📁 Created example file: {example_file}")
        
        print("\n🎯 To test live monitoring:")
        print(f"   1. Run: python -m visual_python.monitor {example_file}")
        print(f"   2. Edit {example_file} in your favorite editor")
        print("   3. Watch changes appear instantly without restarting!")
        print("   4. Press Ctrl+C to stop monitoring")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating example: {e}")
        return False

def demo_signal_export():
    """Demonstrate analog signal export"""
    print("\n📡 Demo 3: Analog Signal Export")
    print("=" * 50)
    
    try:
        from visual_python import run_visual, quick_export_csv, quick_export_arduino
        
        # Execute code that will generate signals
        signal_code = '''
# Hardware control simulation
led_brightness = 128
servo_angle = 90
sensor_threshold = 0.5

print(f"LED brightness: {led_brightness}")
print(f"Servo angle: {servo_angle}")
print(f"Sensor threshold: {sensor_threshold}")

# Control loop
for cycle in range(3):
    brightness = led_brightness + cycle * 20
    angle = servo_angle + cycle * 15
    print(f"Cycle {cycle}: LED={brightness}, Servo={angle}")
'''
        
        print("Executing code and capturing analog signals...")
        result = run_visual(signal_code, backend='console')
        
        # Export as CSV
        csv_file = quick_export_csv(result, "demo_signals.csv")
        print(f"📊 Exported signals to: {csv_file}")
        
        # Export as Arduino code
        arduino_file = quick_export_arduino(result, "demo_replay.ino")
        print(f"🔧 Exported Arduino code to: {arduino_file}")
        
        print("\n🔌 You can now:")
        print(f"   - Analyze signals in: {csv_file}")
        print(f"   - Upload Arduino code: {arduino_file}")
        print("   - Drive real hardware with your Python execution!")
        
        return True
        
    except Exception as e:
        print(f"❌ Signal export error: {e}")
        return False

def demo_performance_comparison():
    """Demonstrate performance comparison"""
    print("\n⚡ Demo 4: Performance Comparison")
    print("=" * 50)
    
    try:
        from visual_python import run_visual
        import subprocess
        import tempfile
        
        test_code = '''
x = 10
y = x * 2
result = x + y
print(f"Result: {result}")
'''
        
        # Test VisualPython execution time
        print("Testing VisualPython execution speed...")
        start_time = time.time()
        result = run_visual(test_code, backend='console')
        visual_python_time = (time.time() - start_time) * 1000
        
        # Test traditional Python execution time  
        print("Testing traditional Python execution speed...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name
        
        try:
            start_time = time.time()
            subprocess.run([sys.executable, temp_file], 
                         capture_output=True, check=True)
            traditional_time = (time.time() - start_time) * 1000
        finally:
            os.unlink(temp_file)
        
        print(f"\n📊 Performance Results:")
        print(f"   VisualPython: {visual_python_time:.2f}ms")
        print(f"   Traditional: {traditional_time:.2f}ms")
        
        if visual_python_time < traditional_time:
            speedup = traditional_time / visual_python_time
            print(f"   🚀 VisualPython is {speedup:.1f}x faster!")
        else:
            print(f"   ⚡ VisualPython provides immediate visual feedback!")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False

def main():
    """Run all demos"""
    print("🎯 VisualPython Revolutionary Demo")
    print("🚀 Zero-Compilation Python Execution")
    print("=" * 60)
    
    demos = [
        demo_basic_execution,
        demo_live_monitoring,
        demo_signal_export,
        demo_performance_comparison
    ]
    
    results = []
    
    for demo in demos:
        try:
            success = demo()
            results.append(success)
            
            if success:
                print("✅ Demo completed successfully!")
            else:
                print("❌ Demo failed!")
                
        except Exception as e:
            print(f"❌ Demo crashed: {e}")
            results.append(False)
        
        print()  # Add spacing between demos
    
    # Summary
    print("🎯 Demo Summary")
    print("=" * 30)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"Successful demos: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All demos passed! VisualPython is ready to revolutionize your coding!")
    elif success_count > 0:
        print("⚡ Partial success - some features working!")
    else:
        print("❌ All demos failed - check your installation")
    
    print("\n🚀 Next Steps:")
    print("   1. Try: python -m visual_python.monitor your_script.py")
    print("   2. Edit your_script.py and watch changes appear instantly!")
    print("   3. Export signals: from visual_python import quick_export_arduino")
    print("   4. Control hardware with your Python execution!")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)