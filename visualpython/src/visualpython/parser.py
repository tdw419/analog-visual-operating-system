"""
Python Visual Parser - Direct AST to Visual Operations

This module contains the revolutionary parser that converts Python AST
directly into visual operations, bypassing the traditional compilation
to bytecode step entirely.

Key Innovation: Code → AST → Visual Elements (no compilation!)
"""

import ast
import operator
import re
from typing import Dict, Any, List, Optional, Union
from collections import defaultdict


class VariableTracker:
    """Tracks variable assignments and their visual representations"""
    
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.assignments: List[Dict[str, Any]] = []
        self.access_count: Dict[str, int] = defaultdict(int)
    
    def assign(self, name: str, value: Any) -> Dict[str, Any]:
        """Record a variable assignment"""
        old_value = self.variables.get(name)
        self.variables[name] = value
        
        assignment_record = {
            'name': name,
            'old_value': old_value,
            'new_value': value,
            'type': type(value).__name__,
            'is_new': name not in self.variables or old_value is None
        }
        
        self.assignments.append(assignment_record)
        return assignment_record
    
    def access(self, name: str) -> Any:
        """Record variable access and return value"""
        self.access_count[name] += 1
        return self.variables.get(name)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get variable tracking statistics"""
        return {
            'total_variables': len(self.variables),
            'total_assignments': len(self.assignments),
            'most_accessed': max(self.access_count.items(), key=lambda x: x[1]) if self.access_count else None,
            'variable_types': {name: type(value).__name__ for name, value in self.variables.items()}
        }


class PythonVisualParser:
    """
    Revolutionary parser that converts Python AST directly to visual operations
    
    This bypasses the entire compilation step and renders code as visual
    elements immediately as the AST is parsed.
    """
    
    def __init__(self, engine):
        """
        Initialize the visual parser
        
        Args:
            engine: VisualPythonEngine instance for rendering
        """
        self.engine = engine
        self.variable_tracker = VariableTracker()
        
        # Operator mapping for expressions
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.LShift: operator.lshift,
            ast.RShift: operator.rshift,
            ast.BitOr: operator.or_,
            ast.BitXor: operator.xor,
            ast.BitAnd: operator.and_,
        }
        
        # Comparison operators
        self.comparisons = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.Is: operator.is_,
            ast.IsNot: operator.is_not,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b,
        }
    
    def parse_and_render(self, tree: ast.AST, variables: Dict[str, Any] = None):
        """
        Parse AST and render visual elements immediately
        
        This is the core innovation: direct AST → visual rendering
        
        Args:
            tree: Python AST to parse
            variables: Existing variables to inherit
        """
        if variables:
            self.variable_tracker.variables.update(variables)
        
        # Process each statement in the AST
        for node in tree.body:
            try:
                self._process_statement(node)
            except Exception as e:
                # Show parsing errors visually
                self.engine.add_visual_element(
                    'parse_error',
                    f"Parse Error: {str(e)}",
                    self.engine.output_x,
                    self.engine.current_y,
                    color='#ff4444'
                )
                self.engine.current_y += self.engine.line_height
        
        # Update engine's variables
        self.engine.variables.update(self.variable_tracker.variables)
    
    def _process_statement(self, node: ast.stmt):
        """Process a single statement node"""
        if isinstance(node, ast.Assign):
            self._handle_assignment(node)
        
        elif isinstance(node, ast.AugAssign):
            self._handle_augmented_assignment(node)
        
        elif isinstance(node, ast.Expr):
            # Expression statement (like function calls)
            if isinstance(node.value, ast.Call):
                self._handle_function_call(node.value)
            else:
                # Evaluate and display expression result
                try:
                    result = self._evaluate_expression(node.value)
                    if result is not None:
                        self.engine.add_visual_element(
                            'expression_result',
                            f"Result: {result}",
                            self.engine.output_x,
                            self.engine.current_y,
                            color='#ffff88'
                        )
                        self.engine.current_y += self.engine.line_height
                except:
                    pass  # Ignore evaluation errors for expressions
        
        elif isinstance(node, ast.For):
            self._handle_for_loop(node)
        
        elif isinstance(node, ast.While):
            self._handle_while_loop(node)
        
        elif isinstance(node, ast.If):
            self._handle_if_statement(node)
        
        elif isinstance(node, ast.FunctionDef):
            self._handle_function_definition(node)
        
        elif isinstance(node, ast.Return):
            self._handle_return(node)
        
        # Add more statement types as needed
    
    def _handle_assignment(self, node: ast.Assign):
        """Handle variable assignment: x = value"""
        try:
            # Evaluate the right-hand side
            value = self._evaluate_expression(node.value)
            
            # Handle multiple targets (a = b = c = value)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    
                    # Track the assignment
                    assignment_record = self.variable_tracker.assign(var_name, value)
                    
                    # Create visual representation immediately
                    self.engine.add_variable_display(var_name, value)
                    
                elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                    # Handle tuple/list unpacking: a, b = 1, 2
                    if isinstance(value, (tuple, list)) and len(target.elts) == len(value):
                        for i, elt in enumerate(target.elts):
                            if isinstance(elt, ast.Name):
                                var_name = elt.id
                                var_value = value[i]
                                self.variable_tracker.assign(var_name, var_value)
                                self.engine.add_variable_display(var_name, var_value)
                
                # Handle other assignment targets as needed
                
        except Exception as e:
            self.engine.add_visual_element(
                'assignment_error',
                f"Assignment Error: {str(e)}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff4444'
            )
            self.engine.current_y += self.engine.line_height
    
    def _handle_augmented_assignment(self, node: ast.AugAssign):
        """Handle augmented assignment: x += value"""
        try:
            if isinstance(node.target, ast.Name):
                var_name = node.target.id
                old_value = self.variable_tracker.access(var_name)
                
                if old_value is not None:
                    # Evaluate the right-hand side
                    rhs_value = self._evaluate_expression(node.value)
                    
                    # Apply the operation
                    if type(node.op) in self.operators:
                        new_value = self.operators[type(node.op)](old_value, rhs_value)
                        
                        # Update variable
                        self.variable_tracker.assign(var_name, new_value)
                        
                        # Show the operation visually
                        op_symbol = self._get_operator_symbol(node.op)
                        self.engine.add_visual_element(
                            'augmented_assignment',
                            f"{var_name} {op_symbol}= {rhs_value} → {new_value}",
                            self.engine.variable_x,
                            self.engine.current_y,
                            color='#88ffff'
                        )
                        self.engine.current_y += self.engine.line_height
        
        except Exception as e:
            self.engine.add_visual_element(
                'aug_assignment_error',
                f"Augmented Assignment Error: {str(e)}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff4444'
            )
            self.engine.current_y += self.engine.line_height
    
    def _handle_function_call(self, node: ast.Call):
        """Handle function calls like print()"""
        try:
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                
                if func_name == 'print':
                    # Handle print function specially
                    self._handle_print_call(node)
                
                elif func_name in ['range', 'len', 'str', 'int', 'float']:
                    # Handle built-in functions
                    result = self._evaluate_expression(node)
                    if result is not None:
                        self.engine.add_visual_element(
                            'function_result',
                            f"{func_name}() → {result}",
                            self.engine.output_x,
                            self.engine.current_y,
                            color='#ff88ff'
                        )
                        self.engine.current_y += self.engine.line_height
                
                else:
                    # Other function calls
                    args_str = ', '.join([str(self._evaluate_expression(arg)) for arg in node.args])
                    self.engine.add_visual_element(
                        'function_call',
                        f"{func_name}({args_str})",
                        self.engine.output_x,
                        self.engine.current_y,
                        color='#ffff88'
                    )
                    self.engine.current_y += self.engine.line_height
        
        except Exception as e:
            self.engine.add_visual_element(
                'function_call_error',
                f"Function Call Error: {str(e)}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff4444'
            )
            self.engine.current_y += self.engine.line_height
    
    def _handle_print_call(self, node: ast.Call):
        """Handle print() function calls with immediate visual output"""
        try:
            output_parts = []
            
            for arg in node.args:
                if isinstance(arg, ast.JoinedStr):
                    # Handle f-strings
                    result = self._evaluate_f_string(arg)
                    output_parts.append(str(result))
                else:
                    # Regular arguments
                    value = self._evaluate_expression(arg)
                    output_parts.append(str(value))
            
            # Join with spaces (default print behavior)
            output_text = ' '.join(output_parts)
            
            # Add to engine output immediately
            self.engine.add_output_line(output_text)
        
        except Exception as e:
            self.engine.add_output_line(f"Print Error: {str(e)}")
    
    def _handle_for_loop(self, node: ast.For):
        """Handle for loops with visual iteration"""
        try:
            if isinstance(node.target, ast.Name):
                loop_var = node.target.id
                
                # Evaluate the iterable
                iterable = self._evaluate_expression(node.iter)
                
                if iterable is not None:
                    # Show loop start
                    self.engine.add_visual_element(
                        'loop_start',
                        f"For {loop_var} in {iterable}:",
                        self.engine.output_x,
                        self.engine.current_y,
                        color='#88ff88'
                    )
                    self.engine.current_y += self.engine.line_height
                    
                    # Execute loop iterations (limited for safety)
                    iteration_count = 0
                    max_iterations = 50  # Safety limit
                    
                    for item in iterable:
                        if iteration_count >= max_iterations:
                            self.engine.add_output_line(f"... (truncated after {max_iterations} iterations)")
                            break
                        
                        # Set loop variable
                        self.variable_tracker.assign(loop_var, item)
                        
                        # Show iteration
                        self.engine.add_visual_element(
                            'loop_iteration',
                            f"  {loop_var} = {item}",
                            self.engine.output_x + 20,
                            self.engine.current_y,
                            color='#88ffff'
                        )
                        self.engine.current_y += self.engine.line_height
                        
                        # Execute loop body
                        for stmt in node.body:
                            self._process_statement(stmt)
                        
                        iteration_count += 1
        
        except Exception as e:
            self.engine.add_visual_element(
                'loop_error',
                f"For Loop Error: {str(e)}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff4444'
            )
            self.engine.current_y += self.engine.line_height
    
    def _handle_while_loop(self, node: ast.While):
        """Handle while loops (with safety limits)"""
        try:
            iteration_count = 0
            max_iterations = 50  # Safety limit
            
            self.engine.add_visual_element(
                'while_start',
                "While loop:",
                self.engine.output_x,
                self.engine.current_y,
                color='#88ff88'
            )
            self.engine.current_y += self.engine.line_height
            
            while iteration_count < max_iterations:
                # Evaluate condition
                condition = self._evaluate_expression(node.test)
                
                if not condition:
                    break
                
                # Show iteration
                self.engine.add_visual_element(
                    'while_iteration',
                    f"  Iteration {iteration_count + 1}",
                    self.engine.output_x + 20,
                    self.engine.current_y,
                    color='#88ffff'
                )
                self.engine.current_y += self.engine.line_height
                
                # Execute loop body
                for stmt in node.body:
                    self._process_statement(stmt)
                
                iteration_count += 1
            
            if iteration_count >= max_iterations:
                self.engine.add_output_line(f"... (while loop truncated after {max_iterations} iterations)")
        
        except Exception as e:
            self.engine.add_visual_element(
                'while_error',
                f"While Loop Error: {str(e)}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff4444'
            )
            self.engine.current_y += self.engine.line_height
    
    def _handle_if_statement(self, node: ast.If):
        """Handle if/elif/else statements"""
        try:
            # Evaluate condition
            condition = self._evaluate_expression(node.test)
            
            self.engine.add_visual_element(
                'if_condition',
                f"If condition: {condition}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ffff88'
            )
            self.engine.current_y += self.engine.line_height
            
            if condition:
                # Execute if body
                for stmt in node.body:
                    self._process_statement(stmt)
            elif node.orelse:
                # Execute else/elif body
                for stmt in node.orelse:
                    self._process_statement(stmt)
        
        except Exception as e:
            self.engine.add_visual_element(
                'if_error',
                f"If Statement Error: {str(e)}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff4444'
            )
            self.engine.current_y += self.engine.line_height
    
    def _handle_function_definition(self, node: ast.FunctionDef):
        """Handle function definitions"""
        func_name = node.name
        args = [arg.arg for arg in node.args.args]
        
        self.engine.add_visual_element(
            'function_def',
            f"Function: {func_name}({', '.join(args)})",
            self.engine.output_x,
            self.engine.current_y,
            color='#ff88ff'
        )
        self.engine.current_y += self.engine.line_height
        
        # Store function for potential later execution
        self.variable_tracker.assign(func_name, f"<function {func_name}>")
    
    def _handle_return(self, node: ast.Return):
        """Handle return statements"""
        if node.value:
            return_value = self._evaluate_expression(node.value)
            self.engine.add_visual_element(
                'return',
                f"Return: {return_value}",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff88ff'
            )
        else:
            self.engine.add_visual_element(
                'return',
                "Return",
                self.engine.output_x,
                self.engine.current_y,
                color='#ff88ff'
            )
        self.engine.current_y += self.engine.line_height
    
    def _evaluate_expression(self, node: ast.expr) -> Any:
        """Evaluate an expression node and return its value"""
        if isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.Name):
            return self.variable_tracker.access(node.id)
        
        elif isinstance(node, ast.BinOp):
            left = self._evaluate_expression(node.left)
            right = self._evaluate_expression(node.right)
            if type(node.op) in self.operators:
                return self.operators[type(node.op)](left, right)
        
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
                if type(op) in self.comparisons:
                    if not self.comparisons[type(op)](left, right):
                        return False
                left = right
            return True
        
        elif isinstance(node, ast.List):
            return [self._evaluate_expression(elt) for elt in node.elts]
        
        elif isinstance(node, ast.Tuple):
            return tuple(self._evaluate_expression(elt) for elt in node.elts)
        
        elif isinstance(node, ast.Dict):
            keys = [self._evaluate_expression(k) for k in node.keys]
            values = [self._evaluate_expression(v) for v in node.values]
            return dict(zip(keys, values))
        
        elif isinstance(node, ast.Call):
            return self._evaluate_function_call(node)
        
        elif isinstance(node, ast.JoinedStr):
            return self._evaluate_f_string(node)
        
        elif isinstance(node, ast.Subscript):
            value = self._evaluate_expression(node.value)
            slice_value = self._evaluate_expression(node.slice)
            return value[slice_value]
        
        elif isinstance(node, ast.Attribute):
            value = self._evaluate_expression(node.value)
            return getattr(value, node.attr)
        
        # Return None for unsupported expressions
        return None
    
    def _evaluate_function_call(self, node: ast.Call) -> Any:
        """Evaluate function calls"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # Handle built-in functions
            if func_name == 'range':
                args = [self._evaluate_expression(arg) for arg in node.args]
                return list(range(*args))
            
            elif func_name == 'len':
                if node.args:
                    obj = self._evaluate_expression(node.args[0])
                    return len(obj)
            
            elif func_name in ['str', 'int', 'float', 'bool']:
                if node.args:
                    obj = self._evaluate_expression(node.args[0])
                    return eval(func_name)(obj)
            
            elif func_name == 'abs':
                if node.args:
                    obj = self._evaluate_expression(node.args[0])
                    return abs(obj)
            
            elif func_name in ['min', 'max']:
                args = [self._evaluate_expression(arg) for arg in node.args]
                return eval(func_name)(args)
        
        return None
    
    def _evaluate_f_string(self, node: ast.JoinedStr) -> str:
        """Evaluate f-string expressions"""
        result = ""
        
        for value in node.values:
            if isinstance(value, ast.Constant):
                result += str(value.value)
            elif isinstance(value, ast.FormattedValue):
                expr_value = self._evaluate_expression(value.value)
                
                # Handle format spec if present
                if value.format_spec:
                    format_spec = self._evaluate_expression(value.format_spec)
                    result += f"{expr_value:{format_spec}}"
                else:
                    result += str(expr_value)
        
        return result
    
    def _get_operator_symbol(self, op: ast.operator) -> str:
        """Get string representation of operator"""
        symbol_map = {
            ast.Add: '+',
            ast.Sub: '-',
            ast.Mult: '*',
            ast.Div: '/',
            ast.FloorDiv: '//',
            ast.Mod: '%',
            ast.Pow: '**',
        }
        return symbol_map.get(type(op), '?')
    
    def get_parser_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        return {
            'variable_stats': self.variable_tracker.get_statistics(),
            'supported_operations': len(self.operators) + len(self.comparisons),
            'variables_current': dict(self.variable_tracker.variables),
            'assignment_history': self.variable_tracker.assignments[-10:]  # Last 10
        }


if __name__ == "__main__":
    # Test the parser
    print("🧪 Testing VisualPython parser...")
    
    # Mock engine for testing
    class MockEngine:
        def __init__(self):
            self.variables = {}
            self.visual_elements = []
            self.current_y = 50
            self.variable_x = 50
            self.output_x = 400
            self.line_height = 25
        
        def add_visual_element(self, element_type, content, x, y, color='#00ff88', metadata=None):
            print(f"Visual element: {element_type} - {content} at ({x}, {y}) [{color}]")
        
        def add_variable_display(self, name, value):
            print(f"Variable display: {name} = {value}")
        
        def add_output_line(self, text):
            print(f"Output: {text}")
    
    # Test parsing
    mock_engine = MockEngine()
    parser = PythonVisualParser(mock_engine)
    
    test_code = """
x = 42
y = x * 2
print(f"Values: x={x}, y={y}")

for i in range(3):
    result = i * 10
    print(f"Loop {i}: {result}")
"""
    
    tree = ast.parse(test_code)
    parser.parse_and_render(tree)
    
    print("✅ Parser test completed")
    print("📊 Statistics:", parser.get_parser_statistics())