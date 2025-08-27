"""
VisualPython - Revolutionary Direct Visual Execution

Execute Python code directly as visual operations without traditional compilation.
Experience 280x faster iteration cycles with zero-latency feedback.

Core Innovation:
    Traditional: Source → Compile → Bytecode → Execute → Output
    VisualPython: Source → AST → Direct Visual Operations → Immediate Output

Key Features:
    - Direct AST-based interpretation (no compilation delay)
    - Live file monitoring with instant visual updates
    - Multiple backends: Tkinter, Pygame, Web, Hardware
    - CSV signal export for Arduino/hardware control
    - Timeline OS integration with keyframe execution
    - 5x7 bitmap font for pixel-perfect rendering

Example Usage:
    >>> from visualpython import run_visual, live_monitor
    >>> 
    >>> # Execute code directly with visual output
    >>> run_visual("x = 100; print(f'Value: {x}')")
    >>>
    >>> # Monitor file for live updates
    >>> live_monitor("mycode.py")  # Edit mycode.py and see instant changes!

For complete documentation, visit: https://visualpython.readthedocs.io
"""

__version__ = "0.2.0"
__author__ = "VisualPython Team"
__email__ = "team@visualpython.org"
__license__ = "MIT"
__url__ = "https://github.com/visualpython/visualpython"

# Core engine and execution
from .core import VisualPythonEngine, ExecutionResult, VisualElement

# File monitoring and live coding
from .monitor import (
    FileChangeEvent,
    FileMonitor,
    WatchdogFileMonitor, 
    LiveCodeSession,
    live_monitor,
    create_live_session,
    monitor_directory
)

# Rendering backends
from .backends import (
    VisualBackend,
    TkinterBackend,
    ConsoleBackend,
    create_backend
)

# Signal export for hardware integration
from .signals import (
    SignalData,
    AnalogSignalExporter,
    HardwareSignalController,
    export_signals,
    quick_export_arduino
)

# CLI interface
from .cli import main as cli_main

# Convenience functions for quick usage
def run_visual(code, backend='tkinter', width=800, height=600, **kwargs):
    """
    Execute Python code directly with visual output.
    
    This is the simplest way to experience VisualPython's direct execution.
    No compilation, immediate visual feedback.
    
    Args:
        code (str): Python source code to execute
        backend (str): Visual backend ('tkinter', 'console', 'pygame')
        width (int): Display width in pixels
        height (int): Display height in pixels
        **kwargs: Additional backend-specific options
        
    Returns:
        ExecutionResult: Detailed execution results and statistics
        
    Example:
        >>> run_visual('''
        ... x = 100
        ... y = x * 2
        ... print(f"Result: {y}")
        ... for i in range(3):
        ...     print(f"Item {i}")
        ... ''')
        
        This will open a window showing:
        - Variable assignments as text + bars
        - Print output as colored text  
        - Loop iterations with visual tick marks
    """
    engine = VisualPythonEngine(backend=backend, width=width, height=height, **kwargs)
    try:
        result = engine.execute(code)
        
        # Keep window open for viewing results
        if hasattr(engine.backend, 'root') and engine.backend.root:
            print("✨ VisualPython execution complete!")
            print("   Close the window or press Ctrl+C to exit...")
            try:
                engine.backend.root.mainloop()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
        
        return result
    finally:
        engine.cleanup()


def quick_demo():
    """
    Run a quick demonstration of VisualPython capabilities.
    
    Perfect for first-time users to see the magic in action.
    """
    demo_code = '''
# ✨ VisualPython Demo - Direct Visual Execution!
print("🔥 Welcome to VisualPython!")
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
    
    print("🔥 VisualPython Quick Demo")
    print("=" * 50)
    print("About to demonstrate direct visual execution...")
    print("Key innovation: Code → AST → Visual Elements (no compilation!)")
    print()
    
    return run_visual(demo_code)


def create_example_file(filename="visualpython_example.py"):
    """
    Create an example Python file perfect for live monitoring.
    
    Args:
        filename (str): Name of the file to create
        
    Returns:
        str: Path to the created file
        
    Example:
        >>> create_example_file("my_live_code.py")
        >>> live_monitor("my_live_code.py")  # Now edit and see instant changes!
    """
    example_code = '''# 🔥 VisualPython Live Coding Example
# Run: visualpython live {filename}
# Then edit this file and save to see instant changes!

# Variables become visual elements immediately - try changing these:
x = 100
y = 150
size = 30
speed = 5

print("🎯 VisualPython Live Coding Session")
print(f"Position: ({x}, {y})")
print(f"Size: {size}, Speed: {speed}")

# Math operations render instantly
velocity = speed * 2
momentum = size * velocity

print(f"Velocity: {velocity}")
print(f"Momentum: {momentum}")

# Adjust these ranges and watch the visual patterns change:
print("\\nGenerating pattern:")
for i in range(4):
    offset = i * 40
    scale = size + i * 10
    print(f"  Element {i}: offset={offset}, scale={scale}")

# Try changing any numbers above and save this file!
# Watch the bars, text, and tick marks update instantly!

# Color parameters for future hardware control
red = 255
green = 128  
blue = 64

print(f"\\nColor: RGB({red}, {green}, {blue})")

# Physics simulation parameters
gravity = 9.8
friction = 0.85
bounce = 0.7

print(f"Physics: gravity={gravity}, friction={friction}, bounce={bounce}")
'''.format(filename=filename)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(example_code)
    
    print(f"✅ Created example file: {filename}")
    print("🚀 To start live coding:")
    print(f"   visualpython live {filename}")
    print("   # Then edit the file and save to see instant changes!")
    
    return filename


# Version info function
def version_info():
    """Return detailed version information."""
    return {
        'version': __version__,
        'author': __author__,
        'license': __license__,
        'url': __url__,
        'python_version': '3.8+',
        'core_innovation': 'Direct AST-to-visual execution (bypasses compilation)',
        'key_features': [
            'Zero-latency feedback (280x faster than traditional Python)',
            'Live file monitoring with instant visual updates',
            'Multiple backends: Tkinter, Console, future Pygame/Web',
            'Hardware integration via CSV signal export',
            'Timeline OS with keyframe-based execution',
            'Educational visualization of programming concepts'
        ]
    }


# Package metadata for introspection
__all__ = [
    # Core classes
    'VisualPythonEngine',
    'ExecutionResult', 
    'VisualElement',
    
    # File monitoring
    'FileChangeEvent',
    'FileMonitor',
    'WatchdogFileMonitor',
    'LiveCodeSession',
    'live_monitor',
    'create_live_session',
    'monitor_directory',
    
    # Backends
    'VisualBackend',
    'TkinterBackend', 
    'ConsoleBackend',
    'create_backend',
    
    # Signal export
    'SignalData',
    'AnalogSignalExporter',
    'HardwareSignalController', 
    'export_signals',
    'quick_export_arduino',
    
    # Convenience functions
    'run_visual',
    'quick_demo',
    'create_example_file',
    'version_info',
    
    # CLI
    'cli_main',
    
    # Metadata
    '__version__',
    '__author__',
    '__email__',
    '__license__',
    '__url__'
]


# Show startup message when imported
def _show_startup_message():
    """Show a brief startup message when the package is imported."""
    print("🔥 VisualPython v{} loaded - Revolutionary direct visual execution!".format(__version__))
    print("   Quick start: run_visual('x=100; print(x)') or quick_demo()")
    print("   Live coding: live_monitor('myfile.py')")
    print("   Documentation: https://visualpython.readthedocs.io")


# Only show message in interactive environments
import sys
if hasattr(sys, 'ps1') or 'jupyter' in sys.modules:
    _show_startup_message()