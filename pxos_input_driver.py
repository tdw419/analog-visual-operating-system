import csv
import sys
import logging
import struct
import pygame
from typing import Dict, List, Optional

# Assumes logger is configured by the host
logger = logging.getLogger(__name__)

# Constants to be used by the host
VK_MAP: Dict[int, str] = {
    pygame.K_BACKSPACE: "backspace", pygame.K_TAB: "tab", pygame.K_RETURN: "enter",
    pygame.K_ESCAPE: "esc", pygame.K_SPACE: "space",
    pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
    pygame.K_F9: "f9", pygame.K_F10: "f10",
    pygame.K_MINUS: "-", pygame.K_PERIOD: ".", pygame.K_SLASH: "/",
    pygame.K_COLON: ":", pygame.K_LEFTBRACKET: "[", pygame.K_RIGHTBRACKET: "]",
}

def pygame_key_to_vk(event: pygame.event.Event) -> Optional[str]:
    """Converts a pygame KEYDOWN event to a virtual keycode string."""
    if event.key in VK_MAP:
        return VK_MAP[event.key]

    # Handle printable ASCII characters
    if 32 <= event.key <= 126:
        return chr(event.key)

    return None


class PXOSInputEngine:
    def __init__(self, vm_memory: List[int], keymap_file: str = "keycodes.csv"):
        self.vm_mem = vm_memory
        self.mailbox_base = 0x1900  # From strict_runner.py MEM class
        self.cmd_key = 0x01         # From strict_runner.py CMD_KEY
        self.keymap = self._load_keymap(keymap_file)

    def _load_keymap(self, filename: str) -> Dict[str, int]:
        """Loads key name to keycode mapping from a CSV file."""
        keymap = {}
        try:
            with open(filename, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    key_name = row['key_name']
                    keycode = int(row['keycode'])
                    keymap[key_name] = keycode
            logger.info(f"Successfully loaded keycode map from '{filename}'")
            return keymap
        except FileNotFoundError:
            logger.error(f"Input driver config file not found: {filename}")
            sys.exit(1)
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing keycode map file '{filename}': {e}")
            sys.exit(1)

    def _write_mailbox(self, cmd: int, arg: int, x: int = 0, y: int = 0):
        """Atomically writes a command to the VM's MAILBOX memory region."""
        try:
            # Using struct to pack integers into the list, assuming vm_mem is a list of ints
            # This is a bit of a hack. A real implementation would use a bytearray.
            # For now, we just assign to the list indices.
            self.vm_mem[self.mailbox_base + 0] = cmd
            self.vm_mem[self.mailbox_base + 1] = arg
            self.vm_mem[self.mailbox_base + 2] = x
            self.vm_mem[self.mailbox_base + 3] = y
            logger.debug(f"Wrote to MAILBOX: cmd={cmd}, arg={arg}")
        except IndexError:
            logger.error("Failed to write to MAILBOX: Memory out of bounds.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during MAILBOX write: {e}")

    def send_key(self, key_name: str):
        """Looks up a key name and writes the corresponding keycode to the MAILBOX."""
        keycode = self.keymap.get(key_name.lower())
        if keycode is not None:
            self._write_mailbox(self.cmd_key, keycode)
        else:
            logger.warning(f"No keycode mapping found for key: '{key_name}'")
