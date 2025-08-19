"""
PXOS Program: UDP Renderer
--------------------------
This program acts as the renderer for the Host Agent bridge.
It listens for UI state information over UDP and renders it.

Hooks:
  - setup(ctx): Initializes the UDP server and state.
  - update(ctx, dt): Receives UDP data and renders the scene.
"""

import socket
import select

# --- Configuration ---
UDP_IP = "127.0.0.1"
UDP_PORT = 9000
MAX_PACKET_SIZE = 1024

# --- State ---
from pxos_py.font import PixelFont

# This dictionary will hold the UI elements to be rendered.
# The key is a unique identifier (e.g., coordinates), and the value is the element data.
ui_state = {}
is_dirty = True # Flag to indicate the screen needs redrawing

def setup(ctx):
    """Initialize the UDP socket, font, and the UI state."""
    ctx.log(f"UDP Renderer: Listening on {UDP_IP}:{UDP_PORT}")

    # Create a non-blocking UDP socket
    ctx.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ctx.sock.setblocking(False)
    try:
        ctx.sock.bind((UDP_IP, UDP_PORT))
    except OSError as e:
        ctx.log(f"ERROR: Could not bind to port {UDP_PORT}. Is another instance running?")
        ctx.log(str(e))
        return

    ctx.log("Socket initialized successfully.")

    # Initialize the font renderer
    ctx.font = PixelFont()
    ctx.log("Font renderer initialized.")

    # Add a reference to the state in the context for easy access
    ctx.ui_state = ui_state
    ctx.is_dirty = is_dirty

def update(ctx, dt):
    """
    Check for UDP packets, update the UI state, and render the screen.
    """
    global is_dirty

    # 1. Receive data from the socket
    ready_to_read, _, _ = select.select([ctx.sock], [], [], 0) # 0 timeout for non-blocking

    if ready_to_read:
        is_dirty = True # Mark dirty if we receive any data
        for sock in ready_to_read:
            while True: # Read all available packets in the buffer
                try:
                    data, addr = sock.recvfrom(MAX_PACKET_SIZE)
                    message = data.decode('utf-8')

                    # 2. Parse the protocol
                    if message == "FRAME_START":
                        # A new frame is starting, clear the old state
                        ui_state.clear()
                    elif message == "FRAME_END":
                        # Frame is complete, we can now render (or wait for the render step)
                        pass # For now, we render on every update if dirty
                    else:
                        parts = message.split('|', 6)
                        if len(parts) == 7 and parts[0] == "TEXT":
                            _, x, y, w, h, role, content = parts
                            # Use position as a simple key for the element
                            key = f"{x},{y}"
                            ui_state[key] = {
                                "type": "text",
                                "x": int(x),
                                "y": int(y),
                                "width": int(w),
                                "height": int(h),
                                "role": role,
                                "content": content
                            }

                except BlockingIOError:
                    # No more packets to read
                    break
                except Exception as e:
                    ctx.log(f"Error processing packet: {e}")
                    break

    # 3. Render the scene (if it has changed)
    if is_dirty:
        fb = getattr(ctx, 'fb', None)
        if fb:
            # Clear the screen (draw background)
            fb.buf.fill(0) # Black background

            # Get the font renderer from the context
            font = getattr(ctx, 'font', None)
            if font:
                # Render each text element from the state
                for element in ui_state.values():
                    if element['type'] == 'text':
                        font.render_string(
                            buffer=fb.buf,
                            x=element['x'],
                            y=element['y'],
                            text=element['content'],
                            color=[0.0, 1.0, 0.0, 1.0] # Green
                        )

        # Reset the dirty flag
        is_dirty = False

# This program doesn't need an on_event handler for now.
# def on_event(ctx, ev):
#     pass
