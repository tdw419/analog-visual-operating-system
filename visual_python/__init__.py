"""
VisualPython - Execute Python code directly as visual operations

This library enables the revolutionary "no compilation" approach to Python execution
where code changes appear instantly on screen without restarting programs.

Key Features:
- Direct Python-to-visual parsing (bypasses bytecode compilation)
- Immediate visual feedback as you type
- Live file monitoring with instant updates
- Export to analog signal data
- Zero restart development workflow

Basic Usage:
    from visual_python import run_visual, live_monitor
    
    # Execute Python visually
    run_visual("x = 50; print(f'Value: {x}')")
    
    # Monitor file for live changes
    live_monitor("my_script.py")

Author: AVOS/UVIR Team
License: MIT
"""

__version__ = "0.1.0"
__author__ = "AVOS/UVIR Team"
__license__ = "MIT"

# Core imports
from .core import VisualPythonEngine, VisualElement, ExecutionResult
from .monitor import FileMonitor, LiveCodeSession, live_monitor, create_live_session
from .backends import TkinterBackend, PyGameBackend, WebBackend
from .parser import PythonVisualParser, VariableTracker
from .signals import AnalogSignalExporter, SignalData

# Convenience functions
def run_visual(code: str, backend='tkinter', **kwargs):
    """
    Execute Python code directly as visual operations
    
    Args:
        code: Python source code to execute
        backend: Visual backend ('tkinter', 'pygame', 'web')
        **kwargs: Additional backend options
        
    Returns:
        ExecutionResult: Result of visual execution
        
    Example:
        run_visual('''
            x = 100
            y = 50
            print(f"Position: {x}, {y}")
            
            for i in range(5):
                print(f"Item {i}: {i * 10}")
        ''')
    """
    engine = VisualPythonEngine(backend=backend, **kwargs)
    result = engine.execute(code)
    return result

def quick_demo():
    """Run a quick demonstration of VisualPython capabilities"""
    demo_code = '''
# VisualPython Demo - No Compilation Required!

# Variables become visual elements immediately
x = 150
y = 100
name = "VisualPython"
count = 42

# Math operations render instantly
width = x * 2
height = y + 50

# Text appears as you type
print("Welcome to VisualPython!")
print(f"System: {name}")
print(f"Variables: x={x}, y={y}")
print(f"Computed: width={width}, height={height}")

# Loops create immediate sequences
print("\\nCounting demo:")
for i in range(count // 10):
    value = i * 5
    print(f"  Step {i}: value = {value}")

print("\\nDemo complete - try editing this code!")
'''
    
    print("🚀 VisualPython Quick Demo")
    print("=" * 50)
    print("Executing Python directly as visual operations...")
    print("No compilation step required!")
    print("=" * 50)
    
    return run_visual(demo_code)

def create_example_file(filename: str = "visual_example.py"):
    """
    Create an example Python file for live monitoring
    
    Args:
        filename: Name of file to create
        
    Returns:
        str: Path to created file
    """
    example_code = '''# VisualPython Live Example
# Edit this file and watch changes appear instantly!

# Try changing these values:
x_position = 100
y_position = 150
color_value = 255
size = 30

# Math becomes visual immediately
calculated_width = size * 2
calculated_height = size + 10

# Output appears as you type
print("Live VisualPython Demo")
print(f"Position: ({x_position}, {y_position})")
print(f"Size: {size} -> Width: {calculated_width}, Height: {calculated_height}")

# Try changing the range or calculations
print("\\nLoop visualization:")
for i in range(3):
    offset = i * 40
    result = x_position + offset
    print(f"  Item {i}: {x_position} + {offset} = {result}")

# Change any value above and watch the output update instantly!
print("\\n✨ Edit this file to see live updates!")
'''
    
    import os
    filepath = os.path.abspath(filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(example_code)
    
    print(f"Created example file: {filepath}")
    print("To start live monitoring, run:")
    print(f"  from visual_python import live_monitor")
    print(f"  live_monitor('{filename}')")
    
    return filepath

# Package metadata
__all__ = [
    # Core classes
    'VisualPythonEngine', 'VisualElement', 'ExecutionResult',
    
    # Monitoring
    'FileMonitor', 'LiveCodeSession', 'live_monitor', 'create_live_session',
    
    # Backends
    'TkinterBackend', 'PyGameBackend', 'WebBackend',
    
    # Parser
    'PythonVisualParser', 'VariableTracker',
    
    # Signals
    'AnalogSignalExporter', 'SignalData',
    
    # Convenience functions
    'run_visual', 'quick_demo', 'create_example_file'
]

# Version info
version_info = tuple(map(int, __version__.split('.')))

# Package configuration
DEFAULT_CONFIG = {
    'backend': 'tkinter',
    'width': 800,
    'height': 600,
    'background_color': '#001122',
    'text_color': '#00ff88',
    'update_interval': 16,  # ~60 FPS
    'font_size': 12,
    'enable_signals': True,
    'enable_export': True,
    'debug_mode': False
}

def get_config():
    """Get current VisualPython configuration"""
    return DEFAULT_CONFIG.copy()

def set_config(**kwargs):
    """Update VisualPython configuration"""
    DEFAULT_CONFIG.update(kwargs)

# Initialize logging
import logging

def setup_logging(level=logging.INFO):
    """Setup VisualPython logging"""
    logger = logging.getLogger('visual_python')
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(level)
    return logger

# Package logger
logger = setup_logging()

# Startup message
def _startup_message():
    """Display startup message when package is imported"""
    if not DEFAULT_CONFIG.get('_startup_shown', False):
        print("🎯 VisualPython v0.1.0 - Revolutionary Zero-Compilation Python")
        print("   Execute Python code directly as visual operations!")
        print("   Try: from visual_python import quick_demo; quick_demo()")
        DEFAULT_CONFIG['_startup_shown'] = True

# Show startup message on first import
_startup_message()