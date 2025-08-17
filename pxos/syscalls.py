"""
PXOS Syscall Dispatcher: The main entry point for kernel operations.
"""
from typing import Dict, Any
from .pixel_buffer import PixelBuffer
from .kernel_plan import sys_plan_apply

class SysDispatcher:
    """
    SysDispatcher routes calls from userland processes to the appropriate
    kernel functions.
    """
    def __init__(self, host: Any, pixel_buffer: PixelBuffer):
        self.host = host
        self.pixel_buffer = pixel_buffer
        self.context = host.context
        print("[KERNEL] Syscall dispatcher initialized.")

    def handle(self, op_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles a syscall operation.
        """
        print(f"[SYSCALL] Received op: '{op_name}' with args: {args}")

        if op_name == "plan":
            plan = args.get("plan")
            if not plan:
                return {"ok": False, "error": "No plan provided"}
            return sys_plan_apply(self.context, plan, dry_run=False)

        elif op_name == "llm":
            prompt = args.get("text", "")
            # In a real system, this would trigger an LLM inference process.
            # Here, we just simulate a response.
            print(f"[SYSCALL] LLM operation (simulated) for prompt: '{prompt}'")
            return {
                "ok": True,
                "response": f"PXOS is a revolutionary pixel-native operating system where all computation exists as visual pixel data."
            }

        elif op_name == "draw":
            # Example of a drawing syscall
            return self.host.draw(args)

        else:
            print(f"[SYSCALL] Error: Unknown operation '{op_name}'")
            return {"ok": False, "error": f"Unknown operation: {op_name}"}
