import ast
import csv

class PythonToCsvTranspiler(ast.NodeVisitor):
    def __init__(self):
        self.csv_ops = []
        self.frame = 0

    def transpile(self, code):
        self.csv_ops = []
        self.frame = 0
        tree = ast.parse(code)
        self.visit(tree)
        return self.csv_ops

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            # For simplicity, we'll just store the value as a string representation
            # A more advanced version would handle different types
            if isinstance(node.value, ast.Constant):
                value = node.value.value
            else:
                # This is a simplification. A real transpiler would need to evaluate expressions.
                value = "expr"
            self.csv_ops.append([self.frame, 'SET_VAR', var_name, value, ''])
            self.frame += 1
        self.generic_visit(node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == 'print':
                if len(call.args) == 1 and isinstance(call.args[0], ast.Constant):
                    text = call.args[0].value
                    self.csv_ops.append([self.frame, 'PRINT', text, '', ''])
                    self.frame += 1
        self.generic_visit(node)

    def visit_For(self, node):
        if (isinstance(node.target, ast.Name) and
                isinstance(node.iter, ast.Call) and
                isinstance(node.iter.func, ast.Name) and
                node.iter.func.id == 'range'):
            loop_var = node.target.id
            if len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Constant):
                start = 0
                stop = node.iter.args[0].value
                self.csv_ops.append([self.frame, 'LOOP_START', loop_var, start, stop])
                self.frame += 1
                for stmt in node.body:
                    self.visit(stmt)
                self.csv_ops.append([self.frame, 'LOOP_END', '', '', ''])
                self.frame += 1
        # Do not call generic_visit here to avoid visiting the loop body twice

def main():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python transpiler.py <input_file> <output_csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_csv = sys.argv[2]

    with open(input_file, 'r') as f:
        code = f.read()

    transpiler = PythonToCsvTranspiler()
    csv_ops = transpiler.transpile(code)

    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['frame', 'op', 'param1', 'param2', 'param3'])
        writer.writerows(csv_ops)

    print(f"Transpiled {input_file} to {output_csv}")

if __name__ == '__main__':
    main()
