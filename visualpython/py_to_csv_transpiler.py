#!/usr/bin/env python3
"""
VisualPython to CSV Transpiler

Converts Python source code directly to CSV operations for analog execution.
This bypasses pixel-level capture and works at the semantic level.

Supports:
- Variable assignments and arithmetic
- Print statements → TEXT operations  
- Loop constructs → Frame sequences
- Basic drawing operations
- Direct Python-to-analog execution model

Usage:
    python py_to_csv_transpiler.py --src script.py --out output.csv
"""

import ast
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Union

# Add visualpython to path  
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

try:
    from visualpython.backends import create_backend
    from visualpython.backends import RecordRenderer
except ImportError:
    print("⚠️  VisualPython modules not found, using standalone CSV writer")
    RecordRenderer = None


class CSVTranspiler:
    """Transpiles Python AST to CSV operations for analog execution"""
    
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.operations = []
        self.frame = 0
        self.variables = {}
        self.current_line_y = 20
        self.line_height = 20
        
    def add_operation(self, op: str, **kwargs):
        """Add a CSV operation"""
        operation = {
            'frame': self.frame,
            'time': 0.0,
            'op': op,
            'x': kwargs.get('x', ''),
            'y': kwargs.get('y', ''),
            'w': kwargs.get('w', ''),
            'h': kwargs.get('h', ''),
            'r': kwargs.get('r', ''),
            'g': kwargs.get('g', ''),
            'b': kwargs.get('b', ''),
            'intensity': kwargs.get('intensity', 1.0),
            'text': kwargs.get('text', ''),
            'id': kwargs.get('id', '')
        }
        self.operations.append(operation)
    
    def next_line_position(self):
        """Get next line position for text output"""
        y = self.current_line_y
        self.current_line_y += self.line_height
        return y
    
    def evaluate_expression(self, node: ast.AST) -> Union[int, float, str]:
        """Evaluate an AST expression to a value"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return self.variables.get(node.id, f"${node.id}")
        elif isinstance(node, ast.BinOp):
            left = self.evaluate_expression(node.left)
            right = self.evaluate_expression(node.right)
            
            # Handle string concatenation and arithmetic
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub) and isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left - right
            elif isinstance(node.op, ast.Mult) and isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left * right
            elif isinstance(node.op, ast.Div) and isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left / right
                
        # Fallback: return string representation
        return f"[{ast.dump(node)}]"
    
    def format_value(self, value: Any) -> str:
        """Format a value for display"""
        if isinstance(value, str):
            return value
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)
    
    def visit_assign(self, node: ast.Assign):
        """Handle variable assignments"""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            value = self.evaluate_expression(node.value)
            self.variables[var_name] = value
            
            # Emit TEXT operation showing the assignment
            display_text = f"{var_name} = {self.format_value(value)}"
            self.add_operation('TEXT', 
                             x=10, y=self.next_line_position(),
                             r=200, g=200, b=255,
                             text=display_text)
    
    def visit_expr(self, node: ast.Expr):
        """Handle expression statements"""
        if isinstance(node.value, ast.Call):
            self.visit_call(node.value)
    
    def visit_call(self, node: ast.Call):
        """Handle function calls"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            if func_name == 'print':
                # Convert print statements to TEXT operations
                if node.args:
                    value = self.evaluate_expression(node.args[0])
                    text = self.format_value(value)
                    self.add_operation('TEXT',
                                     x=10, y=self.next_line_position(),
                                     r=255, g=255, b=255,
                                     text=text)
            
            elif func_name == 'rect':
                # Handle rect(x, y, w, h, r, g, b) calls
                if len(node.args) >= 7:
                    x = self.evaluate_expression(node.args[0])
                    y = self.evaluate_expression(node.args[1]) 
                    w = self.evaluate_expression(node.args[2])
                    h = self.evaluate_expression(node.args[3])
                    r = self.evaluate_expression(node.args[4])
                    g = self.evaluate_expression(node.args[5])
                    b = self.evaluate_expression(node.args[6])
                    
                    self.add_operation('RECT',
                                     x=x, y=y, w=w, h=h,
                                     r=r, g=g, b=b)
            
            elif func_name == 'text':
                # Handle text(x, y, message, r, g, b) calls
                if len(node.args) >= 6:
                    x = self.evaluate_expression(node.args[0])
                    y = self.evaluate_expression(node.args[1])
                    message = self.evaluate_expression(node.args[2])
                    r = self.evaluate_expression(node.args[3])
                    g = self.evaluate_expression(node.args[4])
                    b = self.evaluate_expression(node.args[5])
                    
                    self.add_operation('TEXT',
                                     x=x, y=y,
                                     r=r, g=g, b=b,
                                     text=self.format_value(message))
            
            elif func_name == 'clear':
                # Handle clear(r, g, b) calls
                r = g = b = 0
                if len(node.args) >= 3:
                    r = self.evaluate_expression(node.args[0])
                    g = self.evaluate_expression(node.args[1])
                    b = self.evaluate_expression(node.args[2])
                
                self.add_operation('CLEAR', r=r, g=g, b=b)
            
            elif func_name == 'commit':
                # Handle commit() calls - advance to next frame
                self.add_operation('COMMIT')
                self.frame += 1
                self.current_line_y = 20  # Reset line position for next frame
    
    def visit_for(self, node: ast.For):
        """Handle for loops"""
        if isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                # Handle for i in range(...) loops
                iter_var = node.target.id
                
                # Evaluate range arguments
                range_args = [self.evaluate_expression(arg) for arg in node.iter.args]
                
                if len(range_args) == 1:
                    start, stop, step = 0, range_args[0], 1
                elif len(range_args) == 2:
                    start, stop, step = range_args[0], range_args[1], 1
                else:
                    start, stop, step = range_args[0], range_args[1], range_args[2]
                
                # Execute loop body for each iteration
                for i in range(start, stop, step):
                    self.variables[iter_var] = i
                    for stmt in node.body:
                        self.visit_statement(stmt)
    
    def visit_if(self, node: ast.If):
        """Handle if statements (basic support)"""
        # For now, just execute the if body (simplified)
        # TODO: Add proper condition evaluation
        for stmt in node.body:
            self.visit_statement(stmt)
    
    def visit_statement(self, node: ast.AST):
        """Visit any statement node"""
        if isinstance(node, ast.Assign):
            self.visit_assign(node)
        elif isinstance(node, ast.Expr):
            self.visit_expr(node)
        elif isinstance(node, ast.For):
            self.visit_for(node)
        elif isinstance(node, ast.If):
            self.visit_if(node)
        else:
            # Unknown statement - emit as comment
            self.add_operation('TEXT',
                             x=10, y=self.next_line_position(),
                             r=128, g=128, b=128,
                             text=f"# {ast.dump(node)[:50]}...")
    
    def transpile(self, source_code: str):
        """Transpile Python source to CSV operations"""
        try:
            tree = ast.parse(source_code)
            
            # Add initial clear operation
            self.add_operation('CLEAR', r=0, g=17, b=0)
            
            # Process each top-level statement
            for node in tree.body:
                self.visit_statement(node)
            
            # Add final commit
            self.add_operation('COMMIT')
            
        except SyntaxError as e:
            print(f"❌ Syntax error in source code: {e}")
            return False
        except Exception as e:
            print(f"❌ Transpilation error: {e}")
            return False
        
        return True
    
    def write_csv(self):
        """Write operations to CSV file"""
        import csv
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'frame', 'time', 'op', 'x', 'y', 'w', 'h', 
                'r', 'g', 'b', 'intensity', 'text', 'id'
            ])
            writer.writeheader()
            writer.writerows(self.operations)
        
        print(f"✅ Transpiled to {self.output_path}")
        print(f"📊 Generated {len(self.operations)} operations across {self.frame + 1} frames")


def main():
    parser = argparse.ArgumentParser(
        description="Transpile Python source to CSV operations for analog execution",
        epilog="""
Examples:
  python py_to_csv_transpiler.py --src demo.py --out demo.csv
  python py_to_csv_transpiler.py --src examples/math_demo.py --out output/math.csv

Supported Python constructs:
  - Variable assignments: x = 42
  - Print statements: print("Hello")  
  - For loops: for i in range(10)
  - Function calls: rect(x, y, w, h, r, g, b)
  - Arithmetic: x = a + b * 2
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--src', required=True, help='Input Python source file')
    parser.add_argument('--out', required=True, help='Output CSV file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Read source file
    src_path = Path(args.src)
    if not src_path.exists():
        print(f"❌ Source file not found: {src_path}")
        return 1
    
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except Exception as e:
        print(f"❌ Error reading source file: {e}")
        return 1
    
    if args.verbose:
        print(f"📖 Read source file: {src_path}")
        print(f"📝 Source code ({len(source_code)} characters):")
        print("-" * 40)
        print(source_code)
        print("-" * 40)
    
    # Transpile
    transpiler = CSVTranspiler(args.out)
    if not transpiler.transpile(source_code):
        return 1
    
    # Write CSV
    transpiler.write_csv()
    
    if args.verbose:
        print(f"\n🎯 You can now replay this with:")
        print(f"   python visualpython_unified.py csv play {args.out} --backend sim")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())