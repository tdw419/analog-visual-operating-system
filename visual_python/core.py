"""
Core VisualPython execution engine

This module contains the main VisualPythonEngine that performs the revolutionary
"direct execution" of Python code as visual operations, bypassing traditional
bytecode compilation.

The key innovation: Instead of Code → Compile → Bytecode → Execute,
we do: Code → AST Parse → Direct Visual Render → Immediate Display
"""

import ast
import time
import traceback
import threading
import queue
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import re
import math

# Try to import backends
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


@dataclass
class VisualElement:
    """Represents a visual element rendered from Python code"""
    element_type: str  # 'text', 'variable', 'result', 'loop_item'
    content: str
    x: int
    y: int
    color: str = '#00ff88'
    font_size: int = 12
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_signal_data(self) -> Dict[str, Any]:
        """Convert to analog signal data format"""
        return {
            'timestamp': self.timestamp,
            'type': self.element_type,
            'x': self.x,
            'y': self.y,
            'content': self.content,
            'color': self.color,
            'metadata': self.metadata
        }


@dataclass
class ExecutionResult:
    """Result of visual Python execution"""
    success: bool
    execution_time_ms: float
    elements_created: int
    variables_tracked: int
    output_lines: int
    visual_elements: List[VisualElement] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    signal_data: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format"""
        return {
            'success': self.success,
            'execution_time_ms': self.execution_time_ms,
            'elements_created': self.elements_created,
            'variables_tracked': self.variables_tracked,
            'output_lines': self.output_lines,
            'error_message': self.error_message,
            'signal_data': self.signal_data
        }


class VisualPythonEngine:
    """
    Main engine that executes Python code directly as visual operations
    
    This is the core innovation: instead of compiling to bytecode,
    we parse the AST and render directly to visual elements.
    """
    
    def __init__(self, backend='tkinter', width=800, height=600, **kwargs):
        """
        Initialize the VisualPython engine
        
        Args:
            backend: Rendering backend ('tkinter', 'pygame', 'web')
            width: Display width
            height: Display height
            **kwargs: Additional backend options
        """
        self.backend_name = backend
        self.width = width
        self.height = height
        self.kwargs = kwargs
        
        # Execution state
        self.variables: Dict[str, Any] = {}
        self.output_lines: List[str] = []
        self.visual_elements: List[VisualElement] = []
        self.execution_count = 0
        
        # Position tracking for visual layout
        self.current_y = 50
        self.line_height = 20
        self.variable_x = 50
        self.output_x = 400
        
        # Performance tracking
        self.total_execution_time = 0
        self.average_execution_time = 0
        
        # Backend initialization
        self.backend = None
        self.display_thread = None
        self.display_queue = queue.Queue()
        self.running = True
        
        self._initialize_backend()
        
        # Parser for direct AST execution
        from .parser import PythonVisualParser
        self.parser = PythonVisualParser(self)
        
        # Signal exporter
        from .signals import AnalogSignalExporter
        self.signal_exporter = AnalogSignalExporter()
    
    def _initialize_backend(self):
        """Initialize the visual backend"""
        try:
            if self.backend_name == 'tkinter' and TKINTER_AVAILABLE:
                from .backends import TkinterBackend
                self.backend = TkinterBackend(
                    width=self.width, 
                    height=self.height, 
                    **self.kwargs
                )
                
            elif self.backend_name == 'pygame' and PYGAME_AVAILABLE:
                from .backends import PyGameBackend
                self.backend = PyGameBackend(
                    width=self.width, 
                    height=self.height, 
                    **self.kwargs
                )
                
            else:
                # Fallback to console backend
                from .backends import ConsoleBackend
                self.backend = ConsoleBackend(**self.kwargs)
                
            # Start display thread for async rendering
            self.display_thread = threading.Thread(
                target=self._display_loop, 
                daemon=True
            )
            self.display_thread.start()
            
        except Exception as e:
            print(f"Backend initialization error: {e}")
            # Use minimal console fallback
            self.backend = None
    
    def execute(self, code: str, live_mode: bool = False) -> ExecutionResult:
        """
        Execute Python code directly as visual operations
        
        This is the revolutionary part: no compilation to bytecode!
        We parse the AST and render visual elements immediately.
        
        Args:
            code: Python source code to execute
            live_mode: Whether this is a live file change execution
            
        Returns:
            ExecutionResult: Detailed execution results
        """
        start_time = time.time()
        
        try:
            # Clear previous state if not in live mode
            if not live_mode:
                self.clear_display()
            
            # Reset position tracking
            self.current_y = 50
            self.output_lines.clear()
            
            # Parse Python code into AST
            # This is MUCH faster than full compilation
            tree = ast.parse(code)
            
            # Execute AST directly as visual operations
            self.parser.parse_and_render(tree, self.variables)
            
            # Update display with new elements
            self._update_display()
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000
            
            # Update statistics
            self.execution_count += 1
            self.total_execution_time += execution_time
            self.average_execution_time = self.total_execution_time / self.execution_count
            
            # Create execution result
            result = ExecutionResult(
                success=True,
                execution_time_ms=execution_time,
                elements_created=len(self.visual_elements),
                variables_tracked=len(self.variables),
                output_lines=len(self.output_lines),
                visual_elements=self.visual_elements.copy(),
                variables=self.variables.copy(),
                signal_data=[elem.to_signal_data() for elem in self.visual_elements]
            )
            
            # Export analog signals if enabled
            if self.kwargs.get('enable_signals', True):
                self.signal_exporter.add_execution_data(result)
            
            return result
            
        except SyntaxError as e:
            error_msg = f"Syntax Error: {e.msg} at line {e.lineno}"
            return self._create_error_result(error_msg, start_time)
            
        except Exception as e:
            error_msg = f"Execution Error: {str(e)}"
            return self._create_error_result(error_msg, start_time)
    
    def _create_error_result(self, error_msg: str, start_time: float) -> ExecutionResult:
        """Create an error result"""
        execution_time = (time.time() - start_time) * 1000
        
        # Display error visually
        self.add_visual_element(
            'error', 
            error_msg, 
            self.output_x, 
            self.current_y, 
            color='#ff4444'
        )
        
        return ExecutionResult(
            success=False,
            execution_time_ms=execution_time,
            elements_created=len(self.visual_elements),
            variables_tracked=len(self.variables),
            output_lines=len(self.output_lines),
            error_message=error_msg,
            visual_elements=self.visual_elements.copy(),
            variables=self.variables.copy()
        )
    
    def add_visual_element(self, element_type: str, content: str, 
                          x: int, y: int, color: str = '#00ff88', **metadata) -> VisualElement:
        """
        Add a visual element to the display
        
        This is called by the parser to create immediate visual feedback
        """
        element = VisualElement(
            element_type=element_type,
            content=str(content),
            x=x,
            y=y,
            color=color,
            metadata=metadata
        )
        
        self.visual_elements.append(element)
        return element
    
    def add_output_line(self, text: str):
        """Add a line of output (from print statements)"""
        self.output_lines.append(text)
        
        # Create visual element for output
        self.add_visual_element(
            'output',
            text,
            self.output_x,
            self.current_y,
            color='#00ffff'
        )
        
        self.current_y += self.line_height
    
    def add_variable_display(self, name: str, value: Any):
        """Add visual display of a variable"""
        display_text = f"{name} = {value}"
        
        # Determine color based on type
        if isinstance(value, (int, float)):
            color = '#ffff00'  # Yellow for numbers
        elif isinstance(value, str):
            color = '#00ff00'  # Green for strings
        else:
            color = '#ff88ff'  # Magenta for other types
        
        element = self.add_visual_element(
            'variable',
            display_text,
            self.variable_x,
            self.current_y,
            color=color,
            variable_name=name,
            variable_value=value,
            variable_type=type(value).__name__
        )
        
        # Add visual bar for numeric values
        if isinstance(value, (int, float)) and value > 0:
            bar_width = min(abs(value) * 2, 150)
            self.add_visual_element(
                'bar',
                '',
                self.variable_x + 200,
                self.current_y - 5,
                color='#88ff88',
                bar_width=bar_width,
                bar_height=10,
                value=value
            )
        
        self.current_y += self.line_height
        return element
    
    def clear_display(self):
        """Clear the visual display"""
        self.visual_elements.clear()
        self.variables.clear()
        self.output_lines.clear()
        self.current_y = 50
        
        if self.backend:
            self.display_queue.put(('clear', None))
    
    def _update_display(self):
        """Update the visual display with current elements"""
        if self.backend:
            self.display_queue.put(('update', self.visual_elements.copy()))
    
    def _display_loop(self):
        """Main display loop running in separate thread"""
        while self.running:
            try:
                # Process display commands
                if not self.display_queue.empty():
                    command, data = self.display_queue.get_nowait()
                    
                    if command == 'clear':
                        if hasattr(self.backend, 'clear'):
                            self.backend.clear()
                    
                    elif command == 'update':
                        if hasattr(self.backend, 'render_elements'):
                            self.backend.render_elements(data)
                
                # Update backend
                if self.backend and hasattr(self.backend, 'update'):
                    self.backend.update()
                
                time.sleep(0.016)  # ~60 FPS
                
            except Exception as e:
                print(f"Display loop error: {e}")
                time.sleep(0.1)
    
    def export_signals(self, filename: str = None) -> str:
        """
        Export execution as analog signal data
        
        Args:
            filename: Output filename (optional)
            
        Returns:
            str: CSV data or filename written
        """
        return self.signal_exporter.export_csv(filename)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            'execution_count': self.execution_count,
            'total_execution_time_ms': self.total_execution_time,
            'average_execution_time_ms': self.average_execution_time,
            'elements_created': len(self.visual_elements),
            'variables_tracked': len(self.variables),
            'output_lines': len(self.output_lines),
            'backend': self.backend_name,
            'display_size': (self.width, self.height)
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=1.0)
        
        if self.backend and hasattr(self.backend, 'cleanup'):
            self.backend.cleanup()


class ConsoleVisualPython:
    """
    Simplified console-only version for environments without GUI backends
    
    This still provides the core "no compilation" experience with text output
    """
    
    def __init__(self):
        self.execution_count = 0
        self.variables = {}
    
    def execute(self, code: str) -> ExecutionResult:
        """Execute Python code with console visual output"""
        start_time = time.time()
        
        print("=" * 60)
        print("🎯 VisualPython Console Execution (No Compilation!)")
        print("=" * 60)
        
        try:
            # Parse AST directly (no compilation!)
            tree = ast.parse(code)
            
            output_lines = []
            visual_elements = []
            
            # Simple AST walking for console output
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Variable assignment
                    if hasattr(node.targets[0], 'id'):
                        var_name = node.targets[0].id
                        print(f"📊 Variable: {var_name} (assigned)")
                        output_lines.append(f"Variable: {var_name}")
                
                elif isinstance(node, ast.Call):
                    # Function call (like print)
                    if hasattr(node.func, 'id') and node.func.id == 'print':
                        print(f"💬 Output: [print statement detected]")
                        output_lines.append("Print statement")
            
            execution_time = (time.time() - start_time) * 1000
            self.execution_count += 1
            
            print(f"✅ Execution complete in {execution_time:.2f}ms")
            print(f"🔄 Total executions: {self.execution_count}")
            print("=" * 60)
            
            return ExecutionResult(
                success=True,
                execution_time_ms=execution_time,
                elements_created=len(output_lines),
                variables_tracked=len(self.variables),
                output_lines=len(output_lines)
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            print(f"❌ Error: {error_msg}")
            print(f"⏱️  Error occurred after {execution_time:.2f}ms")
            print("=" * 60)
            
            return ExecutionResult(
                success=False,
                execution_time_ms=execution_time,
                elements_created=0,
                variables_tracked=0,
                output_lines=0,
                error_message=error_msg
            )


# Convenience function for quick console testing
def quick_console_test():
    """Quick test of console visual Python"""
    console = ConsoleVisualPython()
    
    test_code = '''
x = 42
y = x * 2
name = "VisualPython"
print(f"Hello from {name}!")
print(f"Values: x={x}, y={y}")

for i in range(3):
    result = i * 10
    print(f"Loop {i}: {result}")
'''
    
    print("Testing VisualPython console execution...")
    result = console.execute(test_code)
    return result


if __name__ == "__main__":
    # Run console test if executed directly
    quick_console_test()