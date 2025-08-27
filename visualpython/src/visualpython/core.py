"""
Core VisualPython engine for direct visual execution.

This module implements the revolutionary concept of bypassing Python compilation
by parsing AST directly and rendering as visual operations.
"""

import ast
import time
import math
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from .backends import create_backend
from .signals import SignalData


@dataclass
class VisualElement:
    """Represents a visual element in the VisualPython display."""
    element_type: str  # 'variable', 'variable_bar', 'output', 'loop_tick', etc.
    content: str
    x: int
    y: int
    color: str = '#00ff88'
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionResult:
    """Results from executing Python code."""
    execution_time_ms: float
    operation_count: int
    variable_count: int
    error: Optional[str] = None
    success: bool = True


class VisualPythonEngine:
    """
    Revolutionary engine for direct visual execution of Python code.
    
    Bypasses traditional compilation by parsing AST and rendering operations
    immediately as visual elements.
    """
    
    def __init__(self, backend='tkinter', width=800, height=600, **kwargs):
        self.backend_name = backend
        self.width = width
        self.height = height
        self.kwargs = kwargs
        
        # Core state
        self.variables: Dict[str, Any] = {}
        self.operations: List[VisualElement] = []
        self.signals: List[SignalData] = []
        
        # Timeline and keyframes
        self.current_time = 5.0  # Start at keyframe 5 (font foundation)
        self.keyframes: List[Dict[str, Any]] = []
        
        # Execution state
        self.y_offset = 80  # Starting Y position for visual elements
        self.line_height = 25
        self.bar_start_x = 450
        self.print_start_x = 20
        
        # Performance tracking
        self.execution_count = 0
        self.total_execution_time = 0
        
        # Initialize backend
        self.backend = create_backend(backend, width=width, height=height, **kwargs)
        
        # Setup Timeline OS boot sequence
        self._setup_timeline_os()
    
    def _setup_timeline_os(self):
        """Initialize Timeline OS boot sequence and font system."""
        # Timeline OS boot keyframes (0-3)
        boot_keyframes = [
            {
                'time': 0.0,
                'type': 'boot_message',
                'text': 'TIMELINE OS v1.0',
                'color': '#00ffff',
                'x': 20,
                'y': 30
            },
            {
                'time': 1.0,
                'type': 'boot_message', 
                'text': 'INITIALIZING ANALOG CORE',
                'color': '#ffff00',
                'x': 20,
                'y': 45
            },
            {
                'time': 2.0,
                'type': 'boot_message',
                'text': 'LOADING SIGNAL DRIVERS',
                'color': '#ff8800',
                'x': 20,
                'y': 60
            },
            {
                'time': 3.0,
                'type': 'boot_message',
                'text': 'BOOT SEQUENCE COMPLETE',
                'color': '#00ff00',
                'x': 20,
                'y': 75
            },
            {
                'time': 5.0,
                'type': 'font_system',
                'text': 'FONT SYSTEM LOADED',
                'color': '#ffffff',
                'x': 20,
                'y': 20
            }
        ]
        
        self.keyframes.extend(boot_keyframes)
    
    def execute(self, code: str) -> float:
        """
        Execute Python code directly as visual operations.
        
        This is the core revolutionary function that bypasses compilation
        and renders code immediately as visual elements.
        
        Args:
            code: Python source code to execute
            
        Returns:
            Execution time in milliseconds
        """
        start_time = time.time()
        
        try:
            # Clear previous state
            self.operations.clear()
            self.signals.clear()
            self.variables.clear()
            self.y_offset = 80
            
            # Parse code to AST - no compilation!
            tree = ast.parse(code)
            
            # Process each top-level statement
            for node in tree.body:
                self._process_ast_node(node)
            
            # Render all operations
            self._render_operations()
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000
            
            # Update statistics
            self.execution_count += 1
            self.total_execution_time += execution_time
            
            return execution_time
            
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            self._render_error(str(e))
            return error_time
    
    def _process_ast_node(self, node: ast.AST):
        """Process a single AST node as a direct visual operation."""
        if isinstance(node, ast.Assign):
            self._process_assignment(node)
            
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._process_function_call(node.value)
            
        elif isinstance(node, ast.For):
            self._process_for_loop(node)
            
        elif isinstance(node, ast.If):
            self._process_if_statement(node)
            
        elif isinstance(node, ast.While):
            self._process_while_loop(node)
    
    def _process_assignment(self, node: ast.Assign):
        """Process variable assignment as immediate visual operation."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            value = self._evaluate_expression(node.value)
            
            # Store variable
            self.variables[var_name] = value
            
            # Create visual element for variable
            element = VisualElement(
                element_type='variable',
                content=f"{var_name} = {value}",
                x=350,
                y=self.y_offset,
                color='#ffff00'
            )
            self.operations.append(element)
            
            # Create visual bar for numeric values
            if isinstance(value, (int, float)):
                bar_width = min(abs(value) * 2, 200)
                bar_color = '#00ff00' if value >= 0 else '#ff0000'
                
                bar_element = VisualElement(
                    element_type='variable_bar',
                    content='',
                    x=self.bar_start_x,
                    y=self.y_offset - 5,
                    color=bar_color,
                    metadata={
                        'bar_width': bar_width,
                        'bar_height': 15,
                        'value': value
                    }
                )
                self.operations.append(bar_element)
            
            # Add to signals for hardware export
            timestamp = time.time()
            signal = SignalData(
                timestamp=timestamp,
                operation='assign',
                x=350,
                y=self.y_offset,
                r=255 if isinstance(value, (int, float)) and value > 0 else 0,
                g=255,
                b=0,
                variable=var_name,
                value=value
            )
            self.signals.append(signal)
            
            self.y_offset += self.line_height
    
    def _process_function_call(self, node: ast.Call):
        """Process function calls, especially print statements."""
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            if node.args:
                output = str(self._evaluate_expression(node.args[0]))
                
                # Create visual element for print output
                element = VisualElement(
                    element_type='output',
                    content=output,
                    x=self.print_start_x,
                    y=self.y_offset,
                    color='#00ffff'
                )
                self.operations.append(element)
                
                # Add to signals
                timestamp = time.time()
                signal = SignalData(
                    timestamp=timestamp,
                    operation='print',
                    x=self.print_start_x,
                    y=self.y_offset,
                    r=0,
                    g=255,
                    b=255,
                    variable='output',
                    value=output
                )
                self.signals.append(signal)
                
                self.y_offset += self.line_height
    
    def _process_for_loop(self, node: ast.For):
        """Process for loops with visual iteration indicators."""
        if isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                var_name = node.target.id
                
                # Get range parameters
                args = [self._evaluate_expression(arg) for arg in node.iter.args]
                if len(args) == 1:
                    start, stop, step = 0, args[0], 1
                elif len(args) == 2:
                    start, stop, step = args[0], args[1], 1
                else:
                    start, stop, step = args[0], args[1], args[2]
                
                # Create loop header
                loop_header = VisualElement(
                    element_type='loop_start',
                    content=f"for {var_name} in range({start}, {stop}):",
                    x=self.print_start_x,
                    y=self.y_offset,
                    color='#ff88ff'
                )
                self.operations.append(loop_header)
                self.y_offset += self.line_height
                
                # Execute loop iterations
                tick_x = self.print_start_x + 20
                for i in range(start, stop, step):
                    self.variables[var_name] = i
                    
                    # Create tick mark for iteration
                    tick_element = VisualElement(
                        element_type='loop_iteration',
                        content=f"  {var_name} = {i}",
                        x=tick_x,
                        y=self.y_offset,
                        color='#88ff88'
                    )
                    self.operations.append(tick_element)
                    
                    # Add visual tick mark
                    tick_mark = VisualElement(
                        element_type='loop_tick',
                        content='',
                        x=tick_x + 150 + i * 15,
                        y=self.y_offset - 5,
                        color='#00ff00',
                        metadata={'tick_size': 10}
                    )
                    self.operations.append(tick_mark)
                    
                    self.y_offset += self.line_height
                    
                    # Process loop body
                    for body_node in node.body:
                        self._process_ast_node(body_node)
    
    def _process_if_statement(self, node: ast.If):
        """Process if/elif/else statements."""
        condition_result = self._evaluate_expression(node.test)
        
        # Show condition evaluation
        condition_text = f"if {self._ast_to_string(node.test)}: → {bool(condition_result)}"
        
        condition_element = VisualElement(
            element_type='if_condition',
            content=condition_text,
            x=self.print_start_x,
            y=self.y_offset,
            color='#ffff88' if condition_result else '#ff8888'
        )
        self.operations.append(condition_element)
        self.y_offset += self.line_height
        
        # Execute appropriate branch
        if condition_result:
            for body_node in node.body:
                self._process_ast_node(body_node)
        elif node.orelse:
            for else_node in node.orelse:
                self._process_ast_node(else_node)
    
    def _process_while_loop(self, node: ast.While):
        """Process while loops (simplified version)."""
        loop_count = 0
        max_iterations = 1000  # Safety limit
        
        while_header = VisualElement(
            element_type='loop_start',
            content=f"while {self._ast_to_string(node.test)}:",
            x=self.print_start_x,
            y=self.y_offset,
            color='#ff88ff'
        )
        self.operations.append(while_header)
        self.y_offset += self.line_height
        
        while self._evaluate_expression(node.test) and loop_count < max_iterations:
            # Show iteration
            iter_element = VisualElement(
                element_type='loop_iteration',
                content=f"  iteration {loop_count}",
                x=self.print_start_x + 20,
                y=self.y_offset,
                color='#88ff88'
            )
            self.operations.append(iter_element)
            self.y_offset += self.line_height
            
            # Process loop body
            for body_node in node.body:
                self._process_ast_node(body_node)
            
            loop_count += 1
        
        if loop_count >= max_iterations:
            warning_element = VisualElement(
                element_type='error',
                content="  (loop stopped - max iterations reached)",
                x=self.print_start_x + 20,
                y=self.y_offset,
                color='#ff4444'
            )
            self.operations.append(warning_element)
            self.y_offset += self.line_height
    
    def _evaluate_expression(self, node: ast.AST) -> Any:
        """Safely evaluate an AST expression node."""
        if isinstance(node, ast.Constant):
            return node.value
            
        elif isinstance(node, ast.Name):
            return self.variables.get(node.id, 0)
            
        elif isinstance(node, ast.BinOp):
            left = self._evaluate_expression(node.left)
            right = self._evaluate_expression(node.right)
            
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right if right != 0 else 0
            elif isinstance(node.op, ast.Mod):
                return left % right if right != 0 else 0
            elif isinstance(node.op, ast.Pow):
                return left ** right
            elif isinstance(node.op, ast.FloorDiv):
                return left // right if right != 0 else 0
                
        elif isinstance(node, ast.UnaryOp):
            operand = self._evaluate_expression(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.Not):
                return not operand
                
        elif isinstance(node, ast.Compare):
            left = self._evaluate_expression(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._evaluate_expression(comparator)
                if isinstance(op, ast.Eq):
                    if not (left == right):
                        return False
                elif isinstance(op, ast.NotEq):
                    if not (left != right):
                        return False
                elif isinstance(op, ast.Lt):
                    if not (left < right):
                        return False
                elif isinstance(op, ast.LtE):
                    if not (left <= right):
                        return False
                elif isinstance(op, ast.Gt):
                    if not (left > right):
                        return False
                elif isinstance(op, ast.GtE):
                    if not (left >= right):
                        return False
                left = right
            return True
            
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for value in node.values:
                    if not self._evaluate_expression(value):
                        return False
                return True
            elif isinstance(node.op, ast.Or):
                for value in node.values:
                    if self._evaluate_expression(value):
                        return True
                return False
                
        elif isinstance(node, ast.JoinedStr):
            # f-string support
            result = ""
            for value in node.values:
                if isinstance(value, ast.Constant):
                    result += str(value.value)
                elif isinstance(value, ast.FormattedValue):
                    result += str(self._evaluate_expression(value.value))
            return result
            
        elif isinstance(node, ast.Call):
            # Handle built-in functions
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name == 'len' and node.args:
                    arg = self._evaluate_expression(node.args[0])
                    return len(arg) if hasattr(arg, '__len__') else 0
                elif func_name == 'abs' and node.args:
                    return abs(self._evaluate_expression(node.args[0]))
                elif func_name == 'min' and node.args:
                    return min(self._evaluate_expression(arg) for arg in node.args)
                elif func_name == 'max' and node.args:
                    return max(self._evaluate_expression(arg) for arg in node.args)
                elif func_name == 'round' and node.args:
                    value = self._evaluate_expression(node.args[0])
                    digits = self._evaluate_expression(node.args[1]) if len(node.args) > 1 else 0
                    return round(value, digits)
        
        # Default fallback
        return 0
    
    def _ast_to_string(self, node: ast.AST) -> str:
        """Convert AST node back to readable string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.BinOp):
            left = self._ast_to_string(node.left)
            right = self._ast_to_string(node.right)
            op_map = {
                ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/',
                ast.Mod: '%', ast.Pow: '**', ast.FloorDiv: '//'
            }
            op = op_map.get(type(node.op), '?')
            return f"{left} {op} {right}"
        elif isinstance(node, ast.Compare):
            left = self._ast_to_string(node.left)
            result = left
            for op, comparator in zip(node.ops, node.comparators):
                op_map = {
                    ast.Eq: '==', ast.NotEq: '!=', ast.Lt: '<',
                    ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>='
                }
                op_str = op_map.get(type(op), '?')
                right = self._ast_to_string(comparator)
                result += f" {op_str} {right}"
            return result
        else:
            return str(type(node).__name__)
    
    def _render_operations(self):
        """Render all operations to the visual backend."""
        self.backend.clear()
        
        # Render Timeline OS boot sequence
        for keyframe in self.keyframes:
            if keyframe['time'] <= self.current_time:
                if keyframe['type'] == 'boot_message':
                    self.backend.render_text(
                        keyframe['text'],
                        keyframe['x'],
                        keyframe['y'],
                        color=keyframe['color']
                    )
                elif keyframe['type'] == 'font_system':
                    self.backend.render_text(
                        keyframe['text'],
                        keyframe['x'],
                        keyframe['y'],
                        color=keyframe['color']
                    )
        
        # Render all visual operations
        for operation in self.operations:
            if operation.element_type == 'variable':
                self.backend.render_text(
                    operation.content,
                    operation.x,
                    operation.y,
                    color=operation.color
                )
            elif operation.element_type == 'variable_bar':
                bar_width = operation.metadata.get('bar_width', 0)
                bar_height = operation.metadata.get('bar_height', 15)
                self.backend.render_rect(
                    operation.x,
                    operation.y,
                    bar_width,
                    bar_height,
                    color=operation.color
                )
            elif operation.element_type == 'output':
                self.backend.render_text(
                    operation.content,
                    operation.x,
                    operation.y,
                    color=operation.color
                )
            elif operation.element_type in ['loop_start', 'loop_iteration', 'if_condition']:
                self.backend.render_text(
                    operation.content,
                    operation.x,
                    operation.y,
                    color=operation.color
                )
            elif operation.element_type == 'loop_tick':
                tick_size = operation.metadata.get('tick_size', 10)
                self.backend.render_rect(
                    operation.x,
                    operation.y,
                    tick_size,
                    tick_size,
                    color=operation.color
                )
        
        # Update display
        self.backend.update()
    
    def _render_error(self, error_message: str):
        """Render error message to display."""
        self.backend.clear()
        self.backend.render_text(
            "❌ EXECUTION ERROR:",
            20,
            100,
            color='#ff0000'
        )
        self.backend.render_text(
            error_message,
            20,
            125,
            color='#ff4444'
        )
        self.backend.update()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        avg_time = (self.total_execution_time / self.execution_count) if self.execution_count > 0 else 0
        
        return {
            'execution_count': self.execution_count,
            'total_execution_time_ms': self.total_execution_time,
            'average_execution_time_ms': avg_time,
            'variable_count': len(self.variables),
            'operation_count': len(self.operations),
            'signal_count': len(self.signals),
            'current_variables': dict(self.variables),
            'backend': self.backend_name,
            'display_size': (self.width, self.height)
        }
    
    def export_signals(self, filename: str = "signals.csv") -> bool:
        """Export signals to CSV for hardware integration."""
        from .signals import export_signals
        return export_signals(self.signals, filename)
    
    def cleanup(self):
        """Clean up resources."""
        if self.backend:
            self.backend.cleanup()