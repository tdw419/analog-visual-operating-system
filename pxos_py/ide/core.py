from typing import Dict, Any, List

class Node:
    """Base class for all nodes in the visual programming graph."""
    def __init__(self, node_id: str, props: Dict[str, Any] = None):
        self.id = node_id
        self.props = props or {}
        self.inputs = {}
        self.outputs = {}

    def connect_input(self, input_name: str, source_node: 'Node', source_output_name: str):
        self.inputs[input_name] = (source_node, source_output_name)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        The core logic of the node. This method will be overridden by subclasses.
        It takes a dictionary of input values and returns a dictionary of output values.
        """
        raise NotImplementedError

class InputNode(Node):
    """A node that provides input to the graph (e.g., a constant color, a texture)."""
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # For an MVP, this might just return a value from its properties.
        return {"output": self.props.get("value")}

class OutputNode(Node):
    """A node that represents the final output of the graph."""
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # This node consumes the input and doesn't produce an output for other nodes.
        # It signals the end of the graph execution.
        print(f"OutputNode received: {input_data.get('input')}")
        return {}

class ShaderNode(Node):
    """A node that executes a shader-like operation."""
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # In a real implementation, this would compile and run a shader.
        # For the MVP, it can just pass through the data or perform a simple transform.
        code = self.props.get("code", "")
        print(f"Executing shader with code: {code[:30]}...")
        # Simulate applying a shader by returning the input.
        return {"output": input_data.get("input")}

class NodeRegistry:
    """Manages the available node types in the IDE."""
    def __init__(self):
        self._nodes = {}
        self.register_default_nodes()

    def register_node(self, node_type: str, node_class: type):
        self._nodes[node_type] = node_class

    def register_default_nodes(self):
        self.register_node("Input", InputNode)
        self.register_node("Output", OutputNode)
        self.register_node("Shader", ShaderNode)

    def create_node(self, node_type: str, node_id: str, props: Dict[str, Any] = None) -> Node:
        node_class = self._nodes.get(node_type)
        if not node_class:
            raise ValueError(f"Node type '{node_type}' not registered.")
        return node_class(node_id, props)

class Canvas:
    """
    Represents the visual programming canvas where nodes are placed and connected.
    Also responsible for executing the graph.
    """
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.execution_order: List[str] = []

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def _topological_sort(self) -> List[str]:
        """
        Sorts the nodes in the graph topologically for execution.
        This is a simplified implementation. A real one would handle cycles.
        """
        # For an MVP, we can assume a simple, linear graph.
        # A more robust implementation would use Kahn's algorithm or DFS.

        # Simple sort based on connections (very basic)
        sorted_nodes = []
        visited = set()

        def visit(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            node = self.nodes[node_id]
            for source_node, _ in node.inputs.values():
                visit(source_node.id)
            sorted_nodes.append(node_id)

        for node_id in self.nodes:
            visit(node_id)

        return sorted_nodes

    def execute_graph(self):
        """Executes the graph in topological order."""
        self.execution_order = self._topological_sort()
        print(f"Execution order: {self.execution_order}")

        node_outputs = {}

        for node_id in self.execution_order:
            node = self.nodes[node_id]

            # Gather inputs for the current node
            input_values = {}
            for input_name, (source_node, source_output_name) in node.inputs.items():
                if source_node.id in node_outputs:
                    input_values[input_name] = node_outputs[source_node.id].get(source_output_name)

            # Process the node
            outputs = node.process(input_values)
            node_outputs[node.id] = outputs

        print("Graph execution complete.")
