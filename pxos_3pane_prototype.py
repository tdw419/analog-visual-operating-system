#!/usr/bin/env python3
"""
PXOS 3-Pane Prototype with Real Transforms
P1: Python Source | P3: Analog DSL Editor | P5: HLIR JSON View
"""

import tkinter as tk
import json
import asyncio
from threading import Thread
from pxos_sync_engine_enhanced import PXOSEngine, Transforms, Profile, ValidationError
from py_to_hlir_ast import T_py_to_hlir
from pxos_dsl_parser import T_analog_to_hlir, T_hlir_to_analog
from pxos_schema_validator import validate_hlir
from hlir_to_python import hlir_to_python_compact

class TkTextPane:
    """Text pane adapter for Tkinter with echo guard"""
    def __init__(self, widget, pid, engine):
        self.widget = widget
        self.id = pid
        self.engine = engine
        self.pinned = False
        self._last_build_id = -1
        self._updating = False
        
        # Bind events
        widget.bind("<KeyRelease>", self.on_edit)
        widget.bind("<Button-1>", self.on_click)

    def read(self):
        return self.widget.get("1.0", tk.END).strip()

    def write(self, text, *, origin, build_id):
        # Echo guard
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        
        # Prevent recursive updates
        if self._updating:
            return
        self._updating = True
        
        try:
            # Save cursor position
            cursor_pos = self.widget.index(tk.INSERT)
            
            # Update text
            self.widget.delete("1.0", tk.END)
            self.widget.insert(tk.END, text)
            
            # Restore cursor position (best effort)
            try:
                self.widget.mark_set(tk.INSERT, cursor_pos)
            except:
                pass  # Invalid position, ignore
                
            # Update visual state
            self._update_visual_state()
            
        finally:
            self._updating = False

    def splice(self, i0, i1, insert_text, *, origin, build_id):
        """Implement splice for minimal edits"""
        # Echo guard
        if origin == self.id and build_id == self._last_build_id:
            return
        self._last_build_id = build_id
        
        if self._updating:
            return
        self._updating = True
        
        try:
            current_text = self.read()
            
            # Convert character positions to Tkinter indices
            start_idx = f"1.0+{i0}c"
            end_idx = f"1.0+{i1}c"
            
            # Save cursor position
            cursor_pos = self.widget.index(tk.INSERT)
            
            # Perform splice
            self.widget.delete(start_idx, end_idx)
            self.widget.insert(start_idx, insert_text)
            
            # Adjust cursor position if needed
            try:
                self.widget.mark_set(tk.INSERT, cursor_pos)
            except:
                pass
                
            self._update_visual_state()
            
        finally:
            self._updating = False

    def annotate(self, message, *, severity="error"):
        """Show error in status bar or console"""
        color = {"error": "red", "warn": "orange", "info": "blue"}.get(severity, "red")
        print(f"[{self.id}] {severity.upper()}: {message}")
        
        # Highlight text widget border for errors
        if severity == "error":
            self.widget.config(highlightbackground="red", highlightthickness=2)
        else:
            self.widget.config(highlightbackground="gray", highlightthickness=1)

    def clear_diagnostics(self):
        """Clear error highlighting"""
        self.widget.config(highlightbackground="gray", highlightthickness=1)

    def _update_visual_state(self):
        """Update visual state based on pane status"""
        if self.pinned:
            self.widget.config(bg="#ffffcc")  # Light yellow for pinned
        else:
            self.widget.config(bg="white")

    def on_edit(self, event):
        """Handle edit events"""
        if not self._updating:
            self.engine.on_edit(self.id)

    def on_click(self, event):
        """Handle click events (for future pinning UI)"""
        pass

class StatusBar:
    """Simple status bar for the prototype"""
    def __init__(self, parent):
        self.frame = tk.Frame(parent, relief=tk.SUNKEN, bd=1)
        self.frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.label = tk.Label(self.frame, text="Ready", anchor=tk.W)
        self.label.pack(side=tk.LEFT, padx=5)
        
        self.build_label = tk.Label(self.frame, text="Build: 0", anchor=tk.E)
        self.build_label.pack(side=tk.RIGHT, padx=5)

    def set_status(self, text):
        self.label.config(text=text)

    def set_build(self, build_id, origin=None):
        if origin:
            self.build_label.config(text=f"Build: {build_id} (from {origin})")
        else:
            self.build_label.config(text=f"Build: {build_id}")

class PXOS3PaneApp:
    """3-Pane PXOS Prototype Application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PXOS 3-Pane Prototype (Real Transforms)")
        self.root.geometry("1200x800")
        
        # Setup asyncio event loop in background thread
        self.loop = asyncio.new_event_loop()
        self.loop_thread = Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # Initialize engine
        self._setup_engine()
        
        # Build UI
        self._build_ui()
        
        # Setup periodic updates
        self._setup_updates()

    def _run_event_loop(self):
        """Run asyncio event loop in background thread"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _setup_engine(self):
        """Initialize the PXOS engine with real transforms"""
        tr = Transforms()
        tr.T_py_to_hlir = T_py_to_hlir
        tr.T_analog_to_hlir = T_analog_to_hlir
        tr.T_hlir_to_analog = T_hlir_to_analog
        tr.validate_hlir = validate_hlir
        
        # Minimal stubs for missing pipeline components
        tr.lower_hlir_to_llir = lambda h: []
        tr.encode_tiles = lambda llir, ecc: []
        tr.ecc_stats = lambda tiles: {}

        self.engine = PXOSEngine(tr, Profile(), loop=self.loop)

    def _build_ui(self):
        """Build the user interface"""
        # Create main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create text widgets with labels
        self._create_pane(main_frame, "P1: Python Source", 0, 0)
        self._create_pane(main_frame, "P3: Analog DSL Editor", 0, 1) 
        self._create_pane(main_frame, "P5: HLIR JSON View", 0, 2)
        
        # Configure grid weights
        main_frame.columnconfigure((0, 1, 2), weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Create status bar
        self.status_bar = StatusBar(self.root)
        
        # Create sample content
        self._load_sample_content()

    def _create_pane(self, parent, title, row, col):
        """Create a labeled text pane"""
        # Label
        label = tk.Label(parent, text=title, font=("Arial", 10, "bold"))
        label.grid(row=row, column=col, sticky="w", padx=5, pady=2)
        
        # Text widget
        text_widget = tk.Text(parent, width=40, height=30, wrap=tk.WORD)
        text_widget.grid(row=row+1, column=col, sticky="nsew", padx=2, pady=2)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(parent)
        scrollbar.grid(row=row+1, column=col, sticky="nse", padx=2, pady=2)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        
        # Create and register pane adapter
        if title.startswith("P1"):
            pane_id = "P1"
        elif title.startswith("P3"):
            pane_id = "P3"
        elif title.startswith("P5"):
            pane_id = "P5"
        else:
            return
            
        pane = TkTextPane(text_widget, pane_id, self.engine)
        self.engine.register(pane)
        
        # Store reference
        setattr(self, f"pane_{pane_id.lower()}", pane)

    def _load_sample_content(self):
        """Load sample content for demonstration"""
        sample_python = """import viewer_adapter as VA

# Sample PXOS program
width = 40
height = 20

VA.RECT(20, 20, width, height, 64)
VA.SLEEP(30)
VA.DAC_WRITE(1, 180)
VA.COMMIT()"""
        
        self.pane_p1.widget.insert(tk.END, sample_python)

    def _setup_updates(self):
        """Setup periodic UI updates"""
        def update_status():
            # Update build info
            try:
                build_info = self.engine.get_build_info()
                self.status_bar.set_build(
                    build_info['build_id'], 
                    build_info['truth_origin']
                )
                
                # Check for errors
                has_errors = any(
                    hasattr(pane, 'logs') and pane.logs 
                    for pane in [self.pane_p1, self.pane_p3, self.pane_p5]
                    if hasattr(self, f'pane_{pane.id.lower()}')
                )
                
                if has_errors:
                    self.status_bar.set_status("Validation errors present")
                else:
                    self.status_bar.set_status("Ready")
                    
            except Exception as e:
                self.status_bar.set_status(f"Error: {e}")
            
            # Schedule next update
            self.root.after(1000, update_status)
        
        # Start periodic updates
        self.root.after(100, update_status)

    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        finally:
            # Cleanup
            self.loop.call_soon_threadsafe(self.loop.stop)

def main():
    """Main entry point"""
    print("Starting PXOS 3-Pane Prototype...")
    print("Usage:")
    print("- Edit Python code in P1 (left pane)")
    print("- Edit Analog DSL in P3 (middle pane)")  
    print("- View/edit HLIR JSON in P5 (right pane)")
    print("- Changes propagate bidirectionally with echo guards")
    print("- Validation errors shown in console and pane borders")
    print()
    
    app = PXOS3PaneApp()
    app.run()

if __name__ == "__main__":
    main()