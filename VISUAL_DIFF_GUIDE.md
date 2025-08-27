# Visual Diff Guide for PXOS Hall of Drift

This guide explains how to use the visual diff capabilities in the PXOS Hall of Drift Replay Ritual for forensic debugging of HLIR divergences.

## Overview

The Hall of Drift now includes three visual diff modes that help you identify and understand HLIR divergences:

1. **Op Level Diff** - Shows differences at the operation level
2. **Field Level Diff** - Shows differences at the field level within operations
3. **Render Overlay** - Shows pixel-level differences in rendered output

## JSON Diff Components

### `compute_json_diff(canonical_hlir, drifted_hlir)`
Computes a line-by-line diff between two HLIR JSON structures.

**Returns**: A list of tuples `(line_type, line_content)` where `line_type` is one of:
- `removed` - Line present in canonical but not in drifted
- `added` - Line present in drifted but not in canonical
- `unchanged` - Line present in both

### `compute_field_level_diff(canonical_hlir, drifted_hlir)`
Computes field-level differences between HLIR structures.

**Returns**: A dictionary with:
- `added_ops` - Operations present in drifted but not in canonical
- `removed_ops` - Operations present in canonical but not in drifted
- `modified_ops` - Operations that exist in both but have different field values
- `field_changes` - Detailed field-level differences

## Pixel Overlay Components

### `compute_pixel_overlay(canonical_hlir, drifted_hlir, width=256, height=256)`
Computes a pixel-level overlay diff between two HLIR renderings.

**Returns**: A PIL Image with differences highlighted in red over the canonical rendering.

## Visual UI Components

### `TkJsonDiffPane`
A Tkinter widget for displaying JSON diffs with color coding:
- Red text for removed lines
- Green text for added lines
- Black text for unchanged lines

### `TkOverlayPane`
A Tkinter widget for displaying pixel overlay diffs.

### `DiffModeSelector`
A UI component with radio buttons to select diff modes.

## Integration with Hall of Drift

The `HallOfDriftController` automatically detects and uses visual components when available:

```python
# When setting up your panes, pass the visual components:
panes = {
    "P1": text_pane1,
    "P2": text_pane2,
    "P3": text_pane3,
    "P4": TkJsonDiffPane(parent),  # Visual diff pane
    "P5": text_pane5,
    "P6": TkOverlayPane(parent),   # Visual overlay pane
}

controller = HallOfDriftController(engine, panes, storage)
```

## Usage Example

```python
import tkinter as tk
from hall_of_drift import DriftStorage, HallOfDriftController
from visual_diff_ui import TkJsonDiffPane, TkOverlayPane, DiffModeSelector

# Create your UI
root = tk.Tk()
json_frame = tk.Frame(root)
overlay_frame = tk.Frame(root)
controls_frame = tk.Frame(root)

# Create visual components
json_diff_pane = TkJsonDiffPane(json_frame)
overlay_pane = TkOverlayPane(overlay_frame)
storage = DriftStorage()

# Set up panes
panes = {
    "P1": text_pane1,
    "P2": text_pane2,
    "P3": text_pane3,
    "P4": json_diff_pane,
    "P5": text_pane5,
    "P6": overlay_pane,
}

# Create controller
controller = HallOfDriftController(engine, panes, storage)

# Add diff mode selector
diff_selector = DiffModeSelector(controls_frame, controller)

# Open a scroll and view diffs
controller.open_scroll("drift_example_1")
controller.render_diff()
```

## Diff Modes

### Op Level Mode
Shows differences at the operation level. Useful for identifying when entire operations are added, removed, or changed.

### Field Level Mode
Shows differences at the field level within operations. Useful for identifying specific parameter changes (e.g., color values, coordinates).

### Render Overlay Mode
Shows pixel-level differences in the rendered output. Useful for visualizing how changes affect the final display.

## Best Practices

1. **Use Op Level** for high-level overview of changes
2. **Use Field Level** for detailed analysis of parameter changes
3. **Use Render Overlay** to see visual impact of changes
4. **Switch modes during replay** to get different perspectives on the same divergence
5. **Step through operations** to see how differences evolve during the replay

## Customization

You can customize the visual components by subclassing them:

```python
class CustomJsonDiffPane(TkJsonDiffPane):
    def __init__(self, parent):
        super().__init__(parent)
        # Add custom tags for additional highlighting
        self.text_widget.tag_configure("critical", foreground="red", background="yellow")
        
    def show_diff(self, diff_lines):
        # Add custom logic for highlighting critical changes
        super().show_diff(diff_lines)
```

## Troubleshooting

### Issue: Visual components not displaying correctly
**Solution**: Ensure your panes implement the required methods (`show_diff` for JSON pane, `show_overlay` for overlay pane).

### Issue: Diff mode selector not working
**Solution**: Make sure the controller is properly passed to the `DiffModeSelector`.

### Issue: Overlay images not displaying
**Solution**: Verify PIL/Pillow is properly installed and ImageTk is available.

## Extending the System

You can extend the visual diff system by:

1. Adding new diff modes to the controller
2. Creating custom visual components
3. Implementing additional overlay algorithms
4. Adding export functionality for diffs and overlays

The modular design makes it easy to enhance the visual debugging capabilities as needed.