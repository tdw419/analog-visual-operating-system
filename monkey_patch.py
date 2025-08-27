# monkey_patch.py
"""
Optional monkey-patch module for seamless integration with existing viewers.
This allows you to capture operations from existing code without modification.

Usage:
    import monkey_patch
    monkey_patch.patch_your_viewer()
    # Now run your existing viewer and operations will be captured
"""
import viewer_adapter_simple as VA

def patch_visualpython():
    """
    Patch a VisualPython-style module.
    Replace 'your_viewer_module' with your actual module name.
    """
    try:
        import your_viewer_module as vp  # ← replace with your actual viewer module
        
        # Store original functions
        original_rect = getattr(vp, 'rect', None)
        original_commit = getattr(vp, 'commit', None) 
        original_sleep = getattr(vp, 'sleep', None)
        
        # Create patched functions
        def patched_rect(x, y, w, h, gray=255):
            VA.RECT(x, y, w, h, gray)
            if original_rect:
                return original_rect(x, y, w, h, gray)
        
        def patched_commit():
            VA.COMMIT()
            if original_commit:
                return original_commit()
        
        def patched_sleep(ms):
            VA.SLEEP(ms)
            if original_sleep:
                return original_sleep(ms)
        
        # Apply patches
        vp.rect = patched_rect
        vp.commit = patched_commit
        vp.sleep = patched_sleep
        
        print("VisualPython module patched successfully")
        return True
        
    except ImportError:
        print("Warning: Could not import viewer module for patching")
        return False

def patch_graphics_module():
    """
    Example of patching a generic graphics module.
    Adapt this pattern for your specific graphics library.
    """
    try:
        import graphics as gfx  # Replace with actual graphics module
        
        # Store originals
        original_draw_rect = getattr(gfx, 'draw_rectangle', None)
        original_refresh = getattr(gfx, 'refresh', None)
        
        def patched_draw_rect(x, y, width, height, color=None):
            # Convert color to grayscale if needed
            gray = 128  # Default gray
            if color:
                if isinstance(color, (list, tuple)) and len(color) >= 3:
                    gray = int((color[0] + color[1] + color[2]) / 3)
                elif isinstance(color, int):
                    gray = color
            
            VA.RECT(x, y, width, height, gray)
            
            if original_draw_rect:
                return original_draw_rect(x, y, width, height, color)
        
        def patched_refresh():
            VA.COMMIT()
            if original_refresh:
                return original_refresh()
        
        # Apply patches
        gfx.draw_rectangle = patched_draw_rect
        gfx.refresh = patched_refresh
        
        print("Graphics module patched successfully")
        return True
        
    except ImportError:
        print("Warning: Could not import graphics module for patching")
        return False

def patch_matplotlib():
    """
    Example of patching matplotlib for scientific plotting.
    This is more complex but shows the concept.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        # Store original functions
        original_add_patch = plt.gca().add_patch if hasattr(plt.gca(), 'add_patch') else None
        original_show = plt.show
        
        def patched_add_patch(patch):
            # Extract rectangle information if it's a Rectangle patch
            if isinstance(patch, patches.Rectangle):
                x, y = patch.get_xy()
                width = patch.get_width()
                height = patch.get_height()
                
                # Convert color to grayscale
                color = patch.get_facecolor()
                if color:
                    gray = int((color[0] + color[1] + color[2]) * 255 / 3)
                else:
                    gray = 128
                
                VA.RECT(int(x), int(y), int(width), int(height), gray)
            
            if original_add_patch:
                return original_add_patch(patch)
        
        def patched_show(*args, **kwargs):
            VA.COMMIT()
            if original_show:
                return original_show(*args, **kwargs)
        
        # Apply patches
        if hasattr(plt.gca(), 'add_patch'):
            plt.gca().add_patch = patched_add_patch
        plt.show = patched_show
        
        print("Matplotlib patched successfully")
        return True
        
    except ImportError:
        print("Warning: Could not import matplotlib for patching")
        return False

def auto_patch():
    """
    Automatically try to patch common graphics modules.
    Call this to attempt patching of all known modules.
    """
    print("Attempting to auto-patch graphics modules...")
    
    results = []
    results.append(("VisualPython", patch_visualpython()))
    results.append(("Graphics", patch_graphics_module()))
    results.append(("Matplotlib", patch_matplotlib()))
    
    successful = [name for name, success in results if success]
    
    if successful:
        print(f"Successfully patched: {', '.join(successful)}")
    else:
        print("No modules were successfully patched")
    
    return successful

def unpatch():
    """
    Restore original functions (if you stored them).
    This is a placeholder - implement based on your specific needs.
    """
    print("Note: Unpatching not implemented in this example")
    print("Restart Python to restore original functions")

# Example usage patterns
if __name__ == "__main__":
    print("Monkey-patch module loaded")
    print("Available functions:")
    print("  patch_visualpython() - Patch VisualPython-style viewer")
    print("  patch_graphics_module() - Patch generic graphics module")
    print("  patch_matplotlib() - Patch matplotlib")
    print("  auto_patch() - Try to patch all known modules")
    
    # Uncomment to test auto-patching
    # auto_patch()