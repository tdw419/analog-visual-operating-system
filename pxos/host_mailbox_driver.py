from pynput import keyboard
import struct

class HostMailboxDriver:
    def __init__(self, pixel_runner):
        self.runner = pixel_runner
        self.mailbox_base = 0x1900  # As per our protocol

    def write_mailbox(self, cmd: int, payload_a: int = 0, payload_b: int = 0, payload_c: int = 0):
        """
        This method will be called by the keyboard listener. It doesn't write
        directly to memory but instead calls a method on the PixelRunner
        to inject the event. This decouples the driver from the runner's
        internal memory management.
        """
        packet = {
            'cmd': cmd,
            'a': payload_a,
            'b': payload_b,
            'c': payload_c,
        }
        self.runner.inject_mailbox_event(packet)

    def on_press(self, key):
        """
        Handles key press events from the listener.
        """
        try:
            # For alphanumeric keys, key.char will have the character.
            # For special keys, key.vk will have the virtual key code.
            code = None
            if hasattr(key, 'char') and key.char:
                code = ord(key.char)
            elif hasattr(key, 'vk'):
                code = key.vk

            if code:
                # cmd 1 = KeyPress
                self.write_mailbox(cmd=1, payload_a=code)
        except Exception:
            # Broad exception to prevent listener from crashing on unknown keys.
            pass

    def start_listener(self):
        """
        Starts the keyboard listener in a separate thread.
        Returns the listener object.
        """
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        print("HostMailboxDriver: Keyboard listener started.")
        return listener

# This file is intended to be used as a module and imported by other parts
# of the PXOS simulation, not run as a standalone script.
