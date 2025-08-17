#!/usr/bin/env python3
"""
PXOS: Pixel-Native Operating System
Entry point for the revolutionary pixel-based computing platform.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pxos.boot_stage0 import main as boot_stage0
from pxos.trust.anchor import TrustAnchor
from pxos.kernel_plan import register_default_actions, install_memory_ops

class Host:
    """Host system interface for PXOS"""
    def __init__(self):
        self.trust_anchor = TrustAnchor()
        self.context = {}
        # Install in-memory operations for testing
        install_memory_ops(self.context)
        # Register plan action handlers
        register_default_actions(self.context)

    def alloc_buffer(self, w, h):
        print(f"[HOST] Allocating buffer {w}x{h}")
        return {"width": w, "height": h, "data": bytearray(w * h * 4)}

    def log(self, msg):
        print(f"[HOST] {msg}")

    def draw(self, args):
        print(f"[HOST] Drawing: {args}")
        return True

    def io(self, args):
        print(f"[HOST] I/O: {args}")
        return True

    def get_font(self, name):
        print(f"[HOST] Loading font: {name}")
        return {"name": name, "loaded": True}

def main():
    """Main entry point for PXOS"""
    print("🌟 PXOS: Pixel-Native Operating System")
    print("🔥 The Ouroboros Ascends...")

    host = Host()
    try:
        boot_stage0(host)
    except KeyboardInterrupt:
        print("\n👋 PXOS shutting down...")
    except Exception as e:
        print(f"❌ PXOS Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
