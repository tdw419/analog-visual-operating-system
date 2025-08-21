"""
Defines hardware-specific rendering profiles.

Each profile is a dictionary containing the necessary parameters to convert
normalized, device-independent coordinates into a hardware-specific
analog signal timeline.
"""

DEVICE_15_INCH = {
    "name": "Generic 15-inch XY Display",
    "vx_span": 4.0,          # Total voltage swing for X-axis (e.g., -2.0V to +2.0V)
    "vy_span": 4.0,          # Total voltage swing for Y-axis (e.g., -2.0V to +2.0V)
    "vx_center": 0.0,        # Center voltage for X-axis
    "vy_center": 0.0,        # Center voltage for Y-axis
    "vz_on": 3.0,            # Voltage for "beam on"
    "vz_off": 0.0,           # Voltage for "beam off"
    "settle_us": 200,        # Dwell time in microseconds before drawing a stroke
    "invert_y": False,       # Whether to invert the Y-axis
}

DEVICE_17_INCH = {
    "name": "Generic 17-inch XY Display",
    "vx_span": 5.0,          # Wider voltage swing for a larger screen
    "vy_span": 5.0,
    "vx_center": 0.0,
    "vy_center": 0.0,
    "vz_on": 3.0,
    "vz_off": 0.0,
    "settle_us": 250,        # Slightly longer settle time for larger components
    "invert_y": False,
}

# A device with an inverted Y-axis for testing purposes
DEVICE_15_INCH_INV_Y = {
    "name": "Generic 15-inch XY Display (Inverted Y)",
    "vx_span": 4.0,
    "vy_span": 4.0,
    "vx_center": 0.0,
    "vy_center": 0.0,
    "vz_on": 3.0,
    "vz_off": 0.0,
    "settle_us": 200,
    "invert_y": True,
}
