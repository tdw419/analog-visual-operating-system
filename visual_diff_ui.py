# visual_diff_ui.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import base64
from io import BytesIO

class TkJsonDiffPane:
    """A Tkinter pane for displaying JSON diffs with color coding"""
    
    def __init__(self, parent, width=60, height=30):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create a text widget with scrollbar
        self.text_widget = tk.Text(self.frame, width=width, height=height, wrap=tk.WORD)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack the widgets
        self.scrollbar.pack(side="right", fill="y")
        self.text_widget.pack(side="left", fill="both", expand=True)
        
        # Configure tags for color coding
        self.text_widget.tag_configure("removed", foreground="red")
        self.text_widget.tag_configure("added", foreground="green")
        self.text_widget.tag_configure("unchanged", foreground="black")
        
    def show_diff(self, diff_lines):
        """Display the JSON diff with color coding"""
        self.text_widget.configure(state="normal")
        self.text_widget.delete(1.0, tk.END)
        
        for line_type, line in diff_lines:
            self.text_widget.insert(tk.END, line + "\n", line_type)
            
        self.text_widget.configure(state="disabled")
        
    def write(self, content, origin=None, build_id=None):
        """Fallback method to display plain text content (for compatibility)"""
        self.text_widget.configure(state="normal")
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, content)
        self.text_widget.configure(state="disabled")

class TkOverlayPane:
    """A Tkinter pane for displaying pixel overlay diffs"""
    
    def __init__(self, parent, width=300, height=300):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create a canvas for displaying the image
        self.canvas = tk.Canvas(self.frame, width=width, height=height, bg="white")
        self.canvas.pack(fill="both", expand=True)
        
        self.image_on_canvas = None
        
    def show_overlay(self, image):
        """Display the pixel overlay image"""
        # Convert PIL Image to PhotoImage
        photo = ImageTk.PhotoImage(image)
        
        # Clear the canvas
        self.canvas.delete("all")
        
        # Display the image
        self.image_on_canvas = self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            image=photo,
            anchor="center"
        )
        
        # Keep a reference to avoid garbage collection
        self.canvas.image = photo
        
    def write(self, content, origin=None, build_id=None):
        """Fallback method to display text content (for compatibility)"""
        # Clear the canvas
        self.canvas.delete("all")
        
        # Display text content
        self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            text=content,
            fill="black",
            font=("Arial", 12),
            width=self.canvas.winfo_width() - 20
        )

class DiffModeSelector:
    """A UI component for selecting diff modes"""
    
    def __init__(self, parent, controller):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", padx=5, pady=5)
        
        self.controller = controller
        self.mode_var = tk.StringVar(value="op_level")
        
        # Create radio buttons for diff modes
        ttk.Label(self.frame, text="Diff Mode:").pack(side="left")
        
        modes = [
            ("Op Level", "op_level"),
            ("Field Level", "field_level"),
            ("Render Overlay", "render_overlay")
        ]
        
        for text, mode in modes:
            ttk.Radiobutton(
                self.frame,
                text=text,
                variable=self.mode_var,
                value=mode,
                command=self.on_mode_change
            ).pack(side="left", padx=5)
    
    def on_mode_change(self):
        """Handle diff mode change"""
        self.controller.set_diff_mode(self.mode_var.get())
        
    def get_mode(self):
        """Get the current diff mode"""
        return self.mode_var.get()

# Example usage in a Tkinter application
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Visual Diff UI Example")
    root.geometry("800x600")
    
    # Create notebook for tabs
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    
    # Create JSON diff tab
    json_frame = ttk.Frame(notebook)
    notebook.add(json_frame, text="JSON Diff")
    
    json_diff_pane = TkJsonDiffPane(json_frame)
    
    # Create overlay tab
    overlay_frame = ttk.Frame(notebook)
    notebook.add(overlay_frame, text="Pixel Overlay")
    
    overlay_pane = TkOverlayPane(overlay_frame)
    
    # Create diff mode selector
    mode_frame = ttk.Frame(root)
    mode_frame.pack(fill="x")
    
    # For this example, we'll create a mock controller
    class MockController:
        def set_diff_mode(self, mode):
            print(f"Diff mode changed to: {mode}")
    
    diff_selector = DiffModeSelector(mode_frame, MockController())
    
    # Add some sample data
    sample_diff = [
        ("removed", '-   "r": 255,'),
        ("added", '+   "r": 254,'),
        ("unchanged", '    "op": "RECT",'),
        ("unchanged", '    "x": 10,'),
    ]
    
    json_diff_pane.show_diff(sample_diff)
    
    # Create a sample image for the overlay
    from PIL import Image, ImageDraw
    sample_image = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(sample_image)
    draw.rectangle([50, 50, 150, 150], fill="red", outline="black")
    
    overlay_pane.show_overlay(sample_image)
    
    root.mainloop()