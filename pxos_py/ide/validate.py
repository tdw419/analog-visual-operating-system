"""
Validates visual editor graphs against a security policy to prevent
the use of unauthorized nodes or APIs.
"""

# Allow-list for node types that can be used in the graph.
ALLOW_NODES = {"Input", "Shader", "Output", "Mixer", "Value"}

# Allow-list for APIs/keywords that can be used within a node's code property.
ALLOW_APIS  = {
    "blur", "mix", "threshold", "color", "mat3", "mat4",
    "sin", "cos", "time", "uniform", "texture", "uv",
}

def validate_graph(graph: dict) -> tuple[bool, str]:
    """
    Validates a graph from the visual editor.

    Args:
        graph: A dictionary representing the node graph.

    Returns:
        A tuple containing a boolean indicating success and a message.
    """
    if not isinstance(graph, dict) or "nodes" not in graph:
        return False, "Invalid graph format: must be a dict with a 'nodes' key."

    for node in graph.get("nodes", []):
        node_type = node.get("type")
        node_id = node.get("id", "unknown")

        if node_type not in ALLOW_NODES:
            return False, f"Validation failed: node type '{node_type}' in node '{node_id}' is not allowed."

        # For Shader nodes, inspect the code for allowed API usage.
        if node_type == "Shader":
            code = (node.get("props") or {}).get("code", "")

            # This is a simple text search. A more robust solution would use an AST parser
            # for the shader language, but this is a good first step.
            used_apis = {api for api in ALLOW_APIS if api in code}

            if not used_apis:
                return False, f"Validation failed: Shader node '{node_id}' uses no allowed APIs."

    return True, "Graph validation successful."
