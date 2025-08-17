"""
PXOS Boot Stage 1: Initialize system components
"""
import numpy as np
from .syscalls import SysDispatcher
from .pixel_buffer import PixelBuffer
from .ide.chat_tile import ChatTile
from .runtimes.shell import ShellProcess

def main(host, buf_info):
    """Stage 1: Initialize PXOS components"""
    host.log("🚀 PXOS Stage 1: Initializing components...")

    # Create pixel buffer
    width, height = buf_info["width"], buf_info["height"]
    pixel_buffer = PixelBuffer(width, height)
    host.log(f"📱 Created pixel buffer: {width}x{height}")

    # Initialize syscall dispatcher
    dispatcher = SysDispatcher(host, pixel_buffer)
    host.log("⚡ Syscall dispatcher online")

    # Create chat tile
    chat_tile = ChatTile(pixel_buffer, host.context)
    host.log("💬 Chat tile initialized")

    # Initialize shell
    shell = ShellProcess(dispatcher, pixel_buffer, chat_tile)
    host.log("🖥️  Shell process ready")

    # Initial render
    pixel_buffer.clear((20, 20, 40, 255))  # Dark blue background
    chat_tile.render()

    # Start main loop
    host.log("🌟 PXOS ready - Starting main loop...")
    shell.run()
