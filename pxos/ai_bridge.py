"""
PXOS AI Bridge: Connects to LLMs to generate plans from goals.
"""
from typing import Dict, Any

class AIBridge:
    """
    The AI Bridge translates natural language goals into executable plans.
    This is a placeholder implementation that returns a fixed, dummy plan.
    """
    def __init__(self, backend: str = "mock"):
        self.backend = backend
        print(f"[AI] AIBridge initialized with '{self.backend}' backend.")

    def generate_plan(self, goal: str, context: Dict[str, Any]) -> Dict:
        """
        Takes a user goal and system context, and returns a pxplan-1 plan.
        """
        print(f"[AI] Generating plan for goal: '{goal}'")

        # In a real implementation, this would involve a call to an LLM.
        # For now, we return a hardcoded plan for demonstration.

        # A simple keyword-based logic to make the mock slightly more interesting.
        if "note" in goal or "hello" in goal:
            plan = {
                "version": "pxplan-1",
                "actions": [
                    {
                        "action": "new_doc",
                        "params": {"path": "/notes/ai_generated.txt"}
                    },
                    {
                        "action": "edit_text",
                        "params": {
                            "path": "/notes/ai_generated.txt",
                            "insert": f"Content for goal: '{goal}'"
                        }
                    },
                    {
                        "action": "save",
                        "params": {"path": "/notes/ai_generated.txt"}
                    }
                ]
            }
        else:
            # Default plan for unrecognized goals
            plan = {
                "version": "pxplan-1",
                "actions": [
                    {
                        "action": "unknown_action",
                        "params": {"goal": goal}
                    }
                ]
            }

        print(f"[AI] Generated plan: {plan}")
        return plan
