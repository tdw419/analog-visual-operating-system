"""
Command-line interface for VisualPython.

Provides easy-to-use commands for running Python code with direct visual execution.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

from .core import VisualPythonEngine
from .monitor import live_monitor, create_live_session
from .signals import export_signals, quick_export_arduino


def create_example_file(filename: str = "visualpython_example.py") -> str:
    """Create an example Python file for testing VisualPython."""
    example_code = '''# VisualPython Example - Direct Visual Execution
# Edit this file and save to see instant changes!

# Variables become visual elements immediately
x = 100
y = 150
size = 30
speed = 5

print("🔥 VisualPython Direct Execution!")
print(f"Position: ({x}, {y})")
print(f"Size: {size}, Speed: {speed}")

# Math operations render instantly
velocity = speed * 2
momentum = size * velocity

print(f"Velocity: {velocity}")
print(f"Momentum: {momentum}")

# Loops create visual patterns
print("\\nGenerating pattern:")
for i in range(4):
    offset = i * 40
    scale = size + i * 10
    print(f"  Element {i}: offset={offset}, scale={scale}")

# Color parameters for hardware control
red = 255
green = 128
blue = 64

print(f"\\nColor: RGB({red}, {green}, {blue})")

# Try changing any numbers above and save this file!
# Watch the visual bars and text update instantly!
'''
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(example_code)
    
    return filename


def run_command(args):
    """Execute a Python file once with visual output."""
    if not os.path.exists(args.file):
        print(f"❌ Error: File {args.file} not found")
        return 1
    
    print(f"🔥 Running {args.file} with VisualPython...")
    
    try:
        engine = VisualPythonEngine(
            backend=args.backend,
            width=args.width,
            height=args.height
        )
        
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        execution_time = engine.execute(code)
        
        print(f"✅ Executed in {execution_time:.2f}ms")
        print("📊 Variables:", list(engine.variables.keys()))
        print("🎯 Close the window or press Ctrl+C to exit")
        
        # Keep window open
        if hasattr(engine.backend, 'root') and engine.backend.root:
            try:
                engine.backend.root.mainloop()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
        
        engine.cleanup()
        return 0
        
    except Exception as e:
        print(f"❌ Error executing {args.file}: {e}")
        return 1


def live_command(args):
    """Monitor a Python file for live updates."""
    if not os.path.exists(args.file):
        print(f"❌ Error: File {args.file} not found")
        return 1
    
    print(f"🔄 Starting live monitoring of {args.file}...")
    print("✨ Edit the file and save to see instant changes!")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        session = live_monitor(
            args.file,
            backend=args.backend,
            width=args.width,
            height=args.height
        )
        
        if hasattr(session, 'monitor'):
            session.monitor.check_interval = args.interval
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 Live monitoring stopped")
        return 0
    except Exception as e:
        print(f"❌ Error in live monitoring: {e}")
        return 1


def step_command(args):
    """Step through code execution with manual control."""
    if not os.path.exists(args.file):
        print(f"❌ Error: File {args.file} not found")
        return 1
    
    print(f"👟 Starting step mode for {args.file}...")
    print("⏯️  Use SPACE to step through execution")
    
    try:
        engine = VisualPythonEngine(
            backend=args.backend,
            width=args.width,
            height=args.height
        )
        
        engine.stepper_mode = True
        
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        engine.execute(code)
        
        # Add stepper controls to renderer
        if hasattr(engine, 'renderer') and hasattr(engine.renderer, 'add_step_callback'):
            engine.renderer.add_step_callback(
                engine.step_back,
                engine.step_forward,
                engine.play_keyframes
            )
        
        if hasattr(engine.backend, 'root') and engine.backend.root:
            engine.backend.root.mainloop()
        
        engine.cleanup()
        return 0
        
    except Exception as e:
        print(f"❌ Error in step mode: {e}")
        return 1


def demo_command(args):
    """Run a built-in demonstration."""
    print("🎬 VisualPython Demo")
    print("=" * 30)
    
    demo_code = '''# 🔥 VisualPython Demo - Revolutionary Direct Execution!
print("Welcome to VisualPython!")
print("Watch variables become visual elements instantly...")

# Variables appear as text + bars immediately
x = 100
y = 150
size = 30

print(f"Position: ({x}, {y})")
print(f"Size: {size}")

# Math operations render in real-time
width = size * 2
height = size + 10
area = width * height

print(f"Dimensions: {width} x {height}")
print(f"Area: {area}")

# Loops create visual sequences
print("\\nCreating elements:")
for i in range(5):
    offset = i * 25
    element_size = size + i * 5
    print(f"  Element {i}: offset={offset}, size={element_size}")

print("\\n🎯 No compilation, no delays - just immediate visual feedback!")
print("Try editing this code and running live_monitor() for real-time updates!")
'''
    
    try:
        engine = VisualPythonEngine(
            backend=args.backend,
            width=args.width,
            height=args.height
        )
        
        execution_time = engine.execute(demo_code)
        
        print(f"✅ Demo executed in {execution_time:.2f}ms")
        print("🎯 Close the window to continue")
        
        if hasattr(engine.backend, 'root') and engine.backend.root:
            engine.backend.root.mainloop()
        
        engine.cleanup()
        return 0
        
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        return 1


def create_command(args):
    """Create an example project."""
    project_name = args.name
    
    print(f"🏗️  Creating VisualPython project: {project_name}")
    
    # Create project directory
    project_dir = Path(project_name)
    project_dir.mkdir(exist_ok=True)
    
    # Create example file
    example_file = project_dir / "main.py"
    create_example_file(str(example_file))
    
    # Create README
    readme_content = f'''# {project_name}

A VisualPython project for direct visual execution.

## Usage

```bash
# Run once
visualpython run main.py

# Live monitoring (edit main.py and see instant changes)
visualpython live main.py

# Step through execution
visualpython step main.py
```

## Features

- **Zero compilation delay** - see changes instantly
- **Visual variables** - numbers become bars, text appears immediately
- **Live coding** - edit and save to see updates in real-time

## Try This

1. Run live monitoring: `visualpython live main.py`
2. Edit main.py and change any number (e.g., `x = 200`)
3. Save the file
4. Watch the visual output update instantly!

*No compilation, no restarts, no delays - pure visual feedback!*
'''
    
    readme_path = project_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Created project in: {project_dir.absolute()}")
    print(f"📁 Files created:")
    print(f"   - {example_file}")
    print(f"   - {readme_path}")
    print(f"\n🚀 Next steps:")
    print(f"   cd {project_name}")
    print(f"   visualpython live main.py")
    print(f"   # Edit main.py and watch changes appear instantly!")
    
    return 0


def signals_command(args):
    """Export visual signals for hardware integration."""
    if not os.path.exists(args.file):
        print(f"❌ Error: File {args.file} not found")
        return 1
    
    print(f"📡 Exporting signals from {args.file}...")
    
    try:
        engine = VisualPythonEngine(backend='console')  # Use console for signal export
        
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        engine.execute(code)
        
        # Export signals
        signal_file = args.output or "signals.csv"
        export_signals(engine.signals, signal_file)
        
        print(f"✅ Signals exported to: {signal_file}")
        print(f"📊 Total signals: {len(engine.signals)}")
        
        # Generate Arduino code if requested
        if args.arduino:
            arduino_file = args.arduino
            quick_export_arduino(engine.signals, arduino_file)
            print(f"🔧 Arduino code generated: {arduino_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error exporting signals: {e}")
        return 1


def version_command(args):
    """Show version information."""
    from . import __version__
    
    print(f"VisualPython v{__version__}")
    print("Revolutionary direct visual execution of Python code")
    print()
    print("Key features:")
    print("  🔥 Zero compilation delay")
    print("  ⚡ Instant visual feedback")
    print("  🔄 Live file monitoring")
    print("  🎨 Creative coding ready")
    print("  🔧 Hardware integration")
    print()
    print("Repository: https://github.com/visualpython/visualpython")
    print("Documentation: https://visualpython.readthedocs.io")
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="VisualPython - Revolutionary direct visual execution of Python code",
        epilog="Examples:\n"
               "  visualpython demo                    # Run built-in demo\n"
               "  visualpython run script.py           # Execute once\n"
               "  visualpython live script.py          # Live monitoring\n"
               "  visualpython step script.py          # Step through execution\n"
               "  visualpython create myproject        # Create example project",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global options
    parser.add_argument('--version', action='version', version='%(prog)s 0.2.0')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Execute a Python file once')
    run_parser.add_argument('file', help='Python file to execute')
    run_parser.add_argument('--backend', choices=['tkinter', 'console'], default='tkinter',
                           help='Visual backend to use')
    run_parser.add_argument('--width', type=int, default=800, help='Display width')
    run_parser.add_argument('--height', type=int, default=600, help='Display height')
    run_parser.set_defaults(func=run_command)
    
    # Live command
    live_parser = subparsers.add_parser('live', help='Monitor file for live updates')
    live_parser.add_argument('file', help='Python file to monitor')
    live_parser.add_argument('--backend', choices=['tkinter', 'console'], default='tkinter',
                            help='Visual backend to use')
    live_parser.add_argument('--width', type=int, default=800, help='Display width')
    live_parser.add_argument('--height', type=int, default=600, help='Display height')
    live_parser.add_argument('--interval', type=float, default=0.1,
                            help='File check interval in seconds')
    live_parser.set_defaults(func=live_command)
    
    # Step command
    step_parser = subparsers.add_parser('step', help='Step through code execution')
    step_parser.add_argument('file', help='Python file to step through')
    step_parser.add_argument('--backend', choices=['tkinter'], default='tkinter',
                            help='Visual backend to use')
    step_parser.add_argument('--width', type=int, default=800, help='Display width')
    step_parser.add_argument('--height', type=int, default=600, help='Display height')
    step_parser.set_defaults(func=step_command)
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run built-in demonstration')
    demo_parser.add_argument('--backend', choices=['tkinter', 'console'], default='tkinter',
                            help='Visual backend to use')
    demo_parser.add_argument('--width', type=int, default=800, help='Display width')
    demo_parser.add_argument('--height', type=int, default=600, help='Display height')
    demo_parser.set_defaults(func=demo_command)
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create example project')
    create_parser.add_argument('name', help='Project name')
    create_parser.set_defaults(func=create_command)
    
    # Signals command
    signals_parser = subparsers.add_parser('signals', help='Export signals for hardware')
    signals_parser.add_argument('file', help='Python file to process')
    signals_parser.add_argument('--output', '-o', help='Output CSV file (default: signals.csv)')
    signals_parser.add_argument('--arduino', help='Generate Arduino code file')
    signals_parser.set_defaults(func=signals_command)
    
    # Version command
    version_parser = subparsers.add_parser('version', help='Show version information')
    version_parser.set_defaults(func=version_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())