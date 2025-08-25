from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

# This parser is now designed to be compatible with the dictionary-based HLIR
# used by the rest of the new architecture.

dsl_grammar = Grammar(r"""
    program    = _ (statement _)*
    statement  = rect_stmt / sleep_stmt / commit_stmt / dac_stmt / integrate_stmt / filter_stmt / multiply_stmt / sum_stmt

    rect_stmt = "RECT" _ "(" _ args _ ")"
    sleep_stmt = "SLEEP" _ "(" _ number _ ")"
    commit_stmt = "COMMIT" _ "(" _ ")"
    dac_stmt = "DAC_WRITE" _ "(" _ number _ "," _ number _ ")"
    integrate_stmt = "INTEGRATE" _ "(" _ number _ "," _ number _ "," _ number _ ")"
    filter_stmt = "FILTER" _ "(" _ string _ "," _ number _ "," _ number _ "," _ number _ ")"
    multiply_stmt = "MULTIPLY" _ "(" _ number _ "," _ number _ "," _ number _ ")"
    sum_stmt = "SUM" _ "(" _ array _ "," _ number _ ")"

    args = arg (_ "," _ arg)*
    arg = kw_arg / number
    kw_arg = identifier _ "=" _ number

    array = "[" _ (number (_ "," _ number)*)? _ "]"
    identifier = ~"[a-zA-Z_][a-zA-Z0-9_]*"
    number     = ~r"-?\d+(\.\d+)?"
    string     = ~r"\"[^\"]*\""
    _          = ~r"\s*"  # Optional whitespace
""")

class HLIRVisitor(NodeVisitor):
    def visit_program(self, node, visited_children):
        # The `(statement _)*` part returns a list of [statement, _] pairs.
        # We just want the statement results.
        _, statement_groups = visited_children
        return [group[0] for group in statement_groups]

    def visit_statement(self, node, visited_children):
        # Pass up the result from const_stmt, sum_stmt, etc.
        return visited_children[0]

    def visit_rect_stmt(self, node, visited_children):
        # "RECT" _ "(" _ args _ ")"
        # visit_args returns a flat list of numbers.
        _, _, _, _, params, _, _ = visited_children
        return {"op": "RECT", "x": params[0], "y": params[1], "w": params[2], "h": params[3], "r": params[4], "g": params[4], "b": params[4]}

    def visit_sleep_stmt(self, node, visited_children):
        return {"op": "SLEEP", "ms": visited_children[4]}

    def visit_commit_stmt(self, node, visited_children):
        return {"op": "COMMIT"}

    def visit_dac_stmt(self, node, visited_children):
        return {"op": "DAC_WRITE", "ch": visited_children[4], "val": visited_children[8]}

    def visit_integrate_stmt(self, node, visited_children):
        return {"op": "INTEGRATE", "tau": visited_children[4], "src": visited_children[8], "dst": visited_children[12]}

    def visit_filter_stmt(self, node, visited_children):
        return {"op": "FILTER", "type": visited_children[4], "fc": visited_children[8], "src": visited_children[12], "dst": visited_children[16]}

    def visit_multiply_stmt(self, node, visited_children):
        return {"op": "MULTIPLY", "gain": visited_children[4], "src": visited_children[8], "dst": visited_children[12]}

    def visit_sum_stmt(self, node, visited_children):
        return {"op": "SUM", "inputs": visited_children[4], "output": visited_children[8]}

    def visit_args(self, node, visited_children):
        # arg (_ "," _ arg)*
        arg1 = visited_children[0]
        other_args = visited_children[1]
        all_args = [arg1]
        for arg_group in other_args:
            all_args.append(arg_group[3])
        return all_args

    def visit_arg(self, node, visited_children):
        return visited_children[0]

    def visit_kw_arg(self, node, visited_children):
        # Not fully implemented, just returns value for now
        return visited_children[4]

    def visit_array(self, node, visited_children):
        # Correctly unpack the 5 children of the 'array' rule
        _, _, optional_group, _, _ = visited_children
        if not optional_group:
            return []

        # The optional group, when it matches, contains a single node result
        # which is for the `(number (_ "," _ number)*)` part of the grammar.
        numbers_group_result = optional_group[0]

        # This result itself is a list: [first_number_result, list_of_other_number_groups]
        first_num = numbers_group_result[0]
        other_nums_groups = numbers_group_result[1]

        all_nums = [first_num]
        for num_group in other_nums_groups:
            # Each group is `(_ "," _ number)`, we want the number at index 3
            all_nums.append(num_group[3])
        return all_nums

    def visit_number(self, node, visited_children):
        return float(node.text) if '.' in node.text else int(node.text)

    def visit_string(self, node, visited_children):
        return node.text.strip('"')

    def generic_visit(self, node, visited_children):
        return visited_children or node

from pxos_sync_engine import ValidationError

def T_analog_to_hlir(text: str):
    try:
        tree = dsl_grammar.parse(text)
        visitor = HLIRVisitor()
        program = visitor.visit(tree)
        return {"schemaVersion": "pxos-ops/1.0", "meta": {"profile": "default"}, "program": program}
    except Exception as e:
        # Catch parsimonious errors or visitor errors
        raise ValidationError(f"DSL Parse Error: {e}")


def T_hlir_to_analog(hlir: dict):
    lines = []
    for op in hlir.get("program", []):
        op_name = op.get("op")
        if op_name == "RECT":
            lines.append(f"RECT({op['x']},{op['y']},{op['w']},{op['h']},{op['r']})")
        elif op_name == "SLEEP":
            lines.append(f"SLEEP({op['ms']})")
        elif op_name == "COMMIT":
            lines.append("COMMIT()")
        elif op_name == "SUM":
            inputs = ", ".join(map(str, op.get("inputs", [])))
            lines.append(f"SUM([{inputs}], {op.get('output')})")
        # ... add other ops as needed
    return "\n".join(lines)

def parse_dsl(text: str):
    return T_analog_to_hlir(text)

def hlir_to_dsl(hlir: dict):
    return T_hlir_to_analog(hlir)

if __name__ == '__main__':
    dsl_code = """
RECT(20,20,40,20,64)
SLEEP(30)
COMMIT()
    """
    hlir = T_analog_to_hlir(dsl_code)
    import json
    print(json.dumps(hlir, indent=2))
    assert hlir['program'][0]['op'] == 'RECT'
    assert hlir['program'][1]['ms'] == 30
    print("\nSUCCESS: DSL parsed to HLIR.")
