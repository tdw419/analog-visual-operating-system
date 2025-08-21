import pytest
from analog_renderer import render_char_to_em_timeline, map_timeline_to_volts
from device_profiles import DEVICE_15_INCH, DEVICE_17_INCH, DEVICE_15_INCH_INV_Y
from vector_font import SIMPLE_FONT

def test_profile_application_produces_different_voltages():
    """
    Tests that rendering the same char with different profiles results in
    different voltage ranges, but the same number of points in the EM timeline.
    """
    char = 'X'

    # The EM timeline generation depends on settle_us, which can differ between profiles.
    # To isolate the voltage mapping, we generate one EM timeline and map it twice.
    em_timeline = render_char_to_em_timeline(char, settle_us=200) # Use a fixed settle time for consistency

    volt_timeline_15 = map_timeline_to_volts(em_timeline, DEVICE_15_INCH)
    volt_timeline_17 = map_timeline_to_volts(em_timeline, DEVICE_17_INCH)

    # Assertion 1: Number of points should be identical
    assert len(volt_timeline_15) == len(volt_timeline_17)

    # Assertion 2: Voltage values should be different due to different spans
    max_vx_15 = max(v[1] for v in volt_timeline_15)
    max_vx_17 = max(v[1] for v in volt_timeline_17)

    assert max_vx_17 > max_vx_15
    assert max_vx_15 != pytest.approx(max_vx_17)

def test_geometry_correctness():
    """
    Tests that the rendered geometry correctly maps to the device's voltage space.
    """
    char = 'X'
    profile = DEVICE_15_INCH

    em_timeline = render_char_to_em_timeline(char, profile['settle_us'])
    volt_timeline = map_timeline_to_volts(em_timeline, profile)

    # Get only the points where the beam is on (Vz > 0)
    draw_points = [v for v in volt_timeline if v[3] > 0]

    # Get the min/max extents of the 'X' glyph from the source font data
    x_coords = [p[0] for stroke in SIMPLE_FONT[char] for p in stroke]
    min_x_em, max_x_em = min(x_coords), max(x_coords)

    # Calculate the expected min/max voltages based on the profile
    expected_min_vx = profile['vx_center'] + profile['vx_span'] * (min_x_em - 0.5)
    expected_max_vx = profile['vx_center'] + profile['vx_span'] * (max_x_em - 0.5)

    # Find the actual min/max voltages from the rendered output
    actual_min_vx = min(p[1] for p in draw_points)
    actual_max_vx = max(p[1] for p in draw_points)

    # Assert they are approximately equal
    assert actual_min_vx == pytest.approx(expected_min_vx)
    assert actual_max_vx == pytest.approx(expected_max_vx)

def test_y_inversion():
    """
    Tests that the 'invert_y' flag correctly flips the Y-axis voltages.
    """
    char = 'A'  # Use a non-symmetrical char for Y-axis testing

    em_timeline = render_char_to_em_timeline(char, DEVICE_15_INCH['settle_us'])

    # Render with standard and inverted profiles
    volt_timeline_normal = map_timeline_to_volts(em_timeline, DEVICE_15_INCH)
    volt_timeline_inverted = map_timeline_to_volts(em_timeline, DEVICE_15_INCH_INV_Y)

    assert len(volt_timeline_normal) == len(volt_timeline_inverted)

    # Find the first drawing point in each timeline to compare
    first_draw_point_normal = next(v for v in volt_timeline_normal if v[3] > 0)
    first_draw_point_inverted = next(v for v in volt_timeline_inverted if v[3] > 0)

    vy_normal = first_draw_point_normal[2]
    vy_inverted = first_draw_point_inverted[2]

    # If center is 0, vy_inverted should be the negation of vy_normal.
    # vy_inv - vy_center = - (vy_norm - vy_center)
    profile = DEVICE_15_INCH
    assert vy_inverted - profile['vy_center'] == pytest.approx(-(vy_normal - profile['vy_center']))
