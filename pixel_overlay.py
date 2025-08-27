# pixel_overlay.py
from PIL import Image, ImageDraw, ImageChops
from typing import Dict, Any, Tuple

def compute_pixel_overlay(canonical_hlir: Dict[str, Any], drifted_hlir: Dict[str, Any], 
                         width: int = 256, height: int = 256) -> Image.Image:
    """
    Compute a pixel overlay diff between two HLIR renderings.
    Returns a PIL Image with the overlay diff.
    """
    # Create blank images for canonical and drifted renderings
    canonical_img = Image.new("RGB", (width, height), "black")
    drifted_img = Image.new("RGB", (width, height), "black")

    # Draw canonical HLIR rendering
    draw_hlir(canonical_img, canonical_hlir)

    # Draw drifted HLIR rendering
    draw_hlir(drifted_img, drifted_hlir)

    # Compute the pixel overlay diff
    diff_img = ImageChops.difference(canonical_img, drifted_img)

    # Enhance differences for better visibility
    # Convert to grayscale and then enhance
    diff_gray = diff_img.convert('L')
    diff_enhanced = diff_gray.point(lambda x: 255 if x > 10 else 0)  # Threshold to make differences more visible
    
    # Create a red overlay for differences
    red_overlay = Image.new('RGBA', (width, height), (255, 0, 0, 128))  # Semi-transparent red
    
    # Convert base image to RGBA for compositing
    base_img_rgba = canonical_img.convert('RGBA')
    
    # Composite the red overlay where differences exist
    diff_mask = diff_enhanced.convert('L')
    result = Image.composite(red_overlay, base_img_rgba, diff_mask)
    
    return result

def draw_hlir(img: Image.Image, hlir: Dict[str, Any]) -> None:
    """
    Render HLIR to an image.
    This is a simplified rendering - in a real implementation, 
    this would be replaced with your actual rendering logic.
    """
    draw = ImageDraw.Draw(img)
    
    # Draw background from meta if available
    bg_color = (0, 0, 0)  # Default black
    if "meta" in hlir:
        # Extract background color if specified
        pass
    
    # Fill background
    draw.rectangle([0, 0, img.width, img.height], fill=bg_color)
    
    # Draw operations
    for op in hlir.get("program", []):
        if op["op"] == "RECT":
            x, y, w, h = op["x"], op["y"], op["w"], op["h"]
            # Handle color values
            r = op.get("r", op.get("g", 0))
            g = op.get("g", r)
            b = op.get("b", g)
            
            # Ensure values are in valid range
            r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
            
            # Draw rectangle
            draw.rectangle([x, y, x + w, y + h], fill=(r, g, b))
        elif op["op"] == "COMMIT":
            # COMMIT is a control operation, no visual representation
            pass
        elif op["op"] == "SLEEP":
            # SLEEP is a control operation, no visual representation
            pass
        # Add other operations as needed