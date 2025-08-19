#!/usr/bin/env python3
"""
Host Agent for PXOS
-------------------
This agent runs on a host machine (Linux) and uses accessibility APIs
to capture the state of legacy applications. It then sends this state
to the PXOS analog system for rendering.

Phase 1: Text Capture
- Uses AT-SPI to find text in a target application (e.g., gedit).
- Extracts the text content and its on-screen coordinates.
- Prints the result to the console.
"""

import gi
gi.require_version('Atspi', '2.0')
from gi.repository import Atspi

import time
import sys
import socket

# --- Configuration ---
TARGET_APP_NAME = "gedit" # Example target, can be changed
PXOS_IP = "127.0.0.1"
PXOS_PORT = 9000
POLL_INTERVAL_S = 2 # How often to scan for changes

def get_desktop():
    """Gets the root desktop object from the accessibility registry."""
    return Atspi.Registry.get_desktop(0)

def find_app_window(desktop, app_name):
    """Finds the application window for the given application name."""
    for app in desktop:
        if app and app.get_name().lower() == app_name.lower():
            # An application can have multiple frames/windows
            # We'll take the first one that is showing
            for child_index in range(app.get_child_count()):
                window = app.get_child_at_index(child_index)
                if window and window.get_role_name() == 'frame' and window.is_showing():
                    return window
    return None

def extract_text_info(accessible, level=0):
    """
    Recursively traverses the accessibility tree from a starting
    accessible object and yields information about text elements.
    """
    if not accessible:
        return

    try:
        # Role information tells us what the UI element *is*
        role = accessible.get_role_name()

        # Check if this object itself contains text
        if role in ('text', 'label', 'paragraph', 'heading', 'text leaf'):
            try:
                # Get the bounding box of the text element
                extents = accessible.get_extents(Atspi.CoordType.SCREEN)
                if extents.width > 0 and extents.height > 0:
                    text_content = accessible.get_text(0, -1).strip()
                    if text_content:
                        yield {
                            "text": text_content,
                            "x": extents.x,
                            "y": extents.y,
                            "width": extents.width,
                            "height": extents.height,
                            "role": role
                        }
            except Exception:
                # Some text-like objects might not support get_text or get_extents
                pass

        # Recursively explore children
        for i in range(accessible.get_child_count()):
            child = accessible.get_child_at_index(i)
            # Yield results from the recursive call
            yield from extract_text_info(child, level + 1)

    except Exception as e:
        # It's common for some accessibility objects to be stale or invalid
        # print(f"Warning: Could not process accessible object: {e}", file=sys.stderr)
        pass


def main():
    """
    Main loop for the host agent. Periodically scans for the target
    application and sends the text content over UDP.
    """
    print("Host Agent started.")
    print(f"Target application name: '{TARGET_APP_NAME}'")
    print(f"Streaming data to {PXOS_IP}:{PXOS_PORT}")
    print("Make sure an AT-SPI bus is running (usually started automatically with a desktop session).")
    print("You may need to run a command like: `gnome-text-editor` to launch the target.")
    print("-" * 30)

    # Set up UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        desktop = get_desktop()
        if not desktop:
            print("Error: Could not access AT-SPI desktop. Is an accessibility bus running?", file=sys.stderr)
            return

        last_state = set()

        while True:
            target_window = find_app_window(desktop, TARGET_APP_NAME)

            if target_window:

                all_text_elements = list(extract_text_info(target_window))
                current_state = set()

                if all_text_elements:
                    # Send a start of frame message
                    sock.sendto(b"FRAME_START", (PXOS_IP, PXOS_PORT))

                    for element in sorted(all_text_elements, key=lambda item: (item['y'], item['x'])):
                        # Protocol: TYPE|X|Y|WIDTH|HEIGHT|ROLE|CONTENT
                        content = element['text'].replace('|', ' ') # Sanitize content
                        protocol_msg = (
                            f"TEXT|{element['x']}|{element['y']}|"
                            f"{element['width']}|{element['height']}|"
                            f"{element['role']}|{content}"
                        )

                        # Send the data over UDP
                        sock.sendto(protocol_msg.encode('utf-8'), (PXOS_IP, PXOS_PORT))
                        current_state.add(protocol_msg)

                    # Send an end of frame message
                    sock.sendto(b"FRAME_END", (PXOS_IP, PXOS_PORT))

                    if current_state != last_state:
                        print(f"Sent {len(all_text_elements)} text elements to PXOS.")
                        last_state = current_state

                else:
                    if last_state: # Clear the screen if window becomes empty
                        sock.sendto(b"FRAME_START", (PXOS_IP, PXOS_PORT))
                        sock.sendto(b"FRAME_END", (PXOS_IP, PXOS_PORT))
                        print("Target window is empty, sent clear frame.")
                        last_state = set()


            else:
                print(f"'{TARGET_APP_NAME}' window not found. Still searching...", end='\r')

            time.sleep(POLL_INTERVAL_S)

    except KeyboardInterrupt:
        print("\nHost Agent stopped by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        sock.close()
        print("Socket closed.")

if __name__ == "__main__":
    # The AT-SPI library requires a running GLib main loop in some contexts,
    # but for this synchronous, polling-based approach, it's often not
    # strictly necessary. If issues arise with events, integrating a
    # GLib.MainLoop would be the next step.
    main()
