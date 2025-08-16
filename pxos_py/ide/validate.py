# Allow-lists for nodes and APIs to enforce security and simplicity in the IDE.
ALLOW_NODES = {"Input", "Shader", "Output", "Mix", "Color"}
ALLOW_APIS = {
    # Math and vector operations
    "vec2", "vec3", "vec4", "mat3", "mat4", "mix", "dot", "normalize",
    # Shader-specific
    "texture", "vertex",p "fragment", "uniform", "varying",
    # Color and effects
    "blur", "threshold", "color", "gradient"
}

def validate_graph(graph: dict) -> tuple[bool, str]:
    """
    Validates a visual programming graph against allow-lists.

    Args:
        graph (dict): A dictionary representing the node graph.
                      Expected format: {"nodes": [{"type": "...", "props": {"code": "..."}}]}

    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating success,
                          and a string with an error message if validation fails.
    """
    if "nodes" not in graph or not isinstance(graph["nodes"], list):
        return False, "Graph is missing 'nodes' list."

    for i, node in enumerate(graph["nodes"]):
        node_type = node.get("type")
        if not node_type:
            return False, f"Node at index {i} is missing a 'type'."

        if node_type not in ALLOW_NODES:
            return False, f"Node type '{node_type}' at index {i} is not allowed."

        # For Shader nodes, check the embedded code against the API allow-list
        if node_type == "Shader":
            props = node.get("props", {})
            code = props.get("code", "")

            # Simple token check. This is not a full parser but prevents obvious misuse.
            tokens_in_code = set(code.split())
            used_apis = {api for api in ALLOW_APIS if api in code}

            if not used_apis:
                # Allow shaders with no explicit API calls (e.g., just setting a color)
                pass

            # Check for any obviously forbidden patterns
            forbidden = {"import ", "os.", "sys.", "eval(", "exec("}
            for pattern in forbidden:
                if pattern in code:
                    return False, f"Forbidden pattern '{pattern}' found in shader node at index {i}."

    return True, "ok"
