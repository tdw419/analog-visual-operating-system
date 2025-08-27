# hall_of_drift_visual_example.py - Complete example of Hall of Drift with visual diff UI
import tkinter as tk
from tkinter import ttk, scrolledtext
import json
from pathlib import Path
from hall_of_drift import DriftStorage, HallOfDriftController
from visual_diff_ui import TkJsonDiffPane, TkOverlayPane, DiffModeSelector
from pxos_sync_engine_enhanced import PXOSEngine, Transforms, Profile
from transpiler import T_py_to_hlir
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog

class MockPane:
    """A mock pane for testing"""
    def __init__(self, name):
        self.name = name
        self.content = ""
        
    def write(self, content, origin=None, build_id=None):
        self.content = content
        print(f"[{self.name}] Content updated: {content[:50]}...")
        
    def clear_diagnostics(self):
        pass

class HallOfDriftVisualWorkbench(tk.Tk):
    """A complete workbench demonstrating the Hall of Drift with visual diff UI"""
    
    def __init__(self):
        super().__init__()
        self.title("PXOS Hall of Drift - Visual Diff Example")
        self.geometry("1200x800")
        
        # Create a mock engine for demonstration
        self.engine = self.create_mock_engine()
        
        # Create the UI
        self.setup_ui()
        
        # Initialize Hall of Drift components
        self.storage = DriftStorage()
        self.setup_hall_of_drift()
        
    def create_mock_engine(self):
        """Create a mock PXOS engine for demonstration"""
        tr = Transforms()
        tr.T_py_to_hlir = T_py_to_hlir
        tr.T_analog_to_hlir = T_analog_to_hlir
        tr.T_hlir_to_analog = T_hlir_to_analog
        tr.validate_hlir = validate_hlir
        # Mock the cache
        class MockCache:
            def __init__(self):
                self.last_good_hlir = {
                    "schemaVersion": "pxos-ops/1.0",
                    "program": [
                        {"op": "RECT", "x": 10, "y": 10, "w": 50, "h": 50, "r": 255, "g": 0, "b": 0},
                        {"op": "COMMIT"}
                    ]
                }
        class MockEngine:
            def __init__(self):
                self.cache = MockCache()
                class MockBus:
                    def __init__(self):
                        self.build_id = 1
                self.bus = MockBus()
                
            def on_edit(self, origin):
                pass
        return MockEngine()
    
    def setup_ui(self):
        """Set up the main UI components"""
        # Create main paned window
        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True)
        
        # Left side: Hall of Drift controls
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # Right side: Visual diff panes
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        # Hall of Drift controls
        self.setup_hall_controls(left_frame)
        
        # Visual diff panes
        self.setup_visual_panes(right_frame)
        
    def setup_hall_controls(self, parent):
        """Set up Hall of Drift controls"""
        ttk.Label(parent, text="📜 Hall of Drift Controls", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Scroll list
        scrolls_frame = ttk.LabelFrame(parent, text="Drift Scrolls")
        scrolls_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.scrolls_list = tk.Listbox(scrolls_frame)
        self.scrolls_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add some sample scrolls
        self.scrolls_list.insert(tk.END, "drift_example_1")
        self.scrolls_list.insert(tk.END, "drift_example_2")
        
        # Control buttons
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(buttons_frame, text="Open Scroll", command=self.open_scroll).pack(side="left", padx=2)
        ttk.Button(buttons_frame, text="Replay", command=self.replay_drift).pack(side="left", padx=2)
        ttk.Button(buttons_frame, text="Step Forward", command=self.step_forward).pack(side="left", padx=2)
        ttk.Button(buttons_frame, text="Step Back", command=self.step_back).pack(side="left", padx=2)
        
        # Metadata display
        self.metadata_text = scrolledtext.ScrolledText(parent, height=6)
        self.metadata_text.pack(fill="x", padx=5, pady=5)
        
    def setup_visual_panes(self, parent):
        """Set up the visual diff panes"""
        # Create notebook for different views
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # JSON Diff tab
        json_frame = ttk.Frame(notebook)
        notebook.add(json_frame, text="JSON Diff")
        self.json_diff_pane = TkJsonDiffPane(json_frame)
        
        # Pixel Overlay tab
        overlay_frame = ttk.Frame(notebook)
        notebook.add(overlay_frame, text="Pixel Overlay")
        self.overlay_pane = TkOverlayPane(overlay_frame)
        
        # Diff mode selector
        self.diff_selector_frame = ttk.Frame(parent)
        self.diff_selector_frame.pack(fill="x", padx=5, pady=5)
        
    def setup_hall_of_drift(self):
        """Set up the Hall of Drift controller"""
        # Create mock panes
        self.panes = {
            "P1": MockPane("P1"),
            "P2": MockPane("P2"),
            "P3": MockPane("P3"),
            "P4": self.json_diff_pane,
            "P5": MockPane("P5"),
            "P6": self.overlay_pane
        }
        
        # Create controller
        self.controller = HallOfDriftController(self.engine, self.panes, self.storage)
        
        # Add diff mode selector
        self.diff_selector = DiffModeSelector(self.diff_selector_frame, self.controller)
        
        # Create sample drift data for demonstration
        self.create_sample_drift_data()
        
    def create_sample_drift_data(self):
        """Create sample drift data for demonstration"""
        # Create sample directory structure
        sample_dir = Path("hall_of_drift") / "drift_example_1"
        sample_dir.mkdir(parents=True, exist_ok=True)
        
        # Sample canonical HLIR
        canonical = {
            "schemaVersion": "pxos-ops/1.0",
            "program": [
                {"op": "RECT", "x": 10, "y": 10, "w": 50, "h": 50, "r": 255, "g": 0, "b": 0},
                {"op": "COMMIT"}
            ]
        }
        
        # Sample drifted HLIR (slightly different)
        drifted = {
            "schemaVersion": "pxos-ops/1.0",
            "program": [
                {"op": "RECT", "x": 10, "y": 10, "w": 50, "h": 50, "r": 250, "g": 10, "b": 0},  # Different color
                {"op": "COMMIT"}
            ]
        }
        
        # Write sample files
        with open(sample_dir / "canonical.json", "w") as f:
            json.dump(canonical, f, indent=2)
            
        with open(sample_dir / "drifted.json", "w") as f:
            json.dump(drifted, f, indent=2)
            
        with open(sample_dir / "path.txt", "w") as f:
            f.write("P1 -> P3 -> P5")
            
        with open(sample_dir / "seed.txt", "w") as f:
            f.write("12345")
            
        # Create second sample
        sample_dir2 = Path("hall_of_drift") / "drift_example_2"
        sample_dir2.mkdir(parents=True, exist_ok=True)
        
        with open(sample_dir2 / "canonical.json", "w") as f:
            json.dump(canonical, f, indent=2)
            
        drifted2 = {
            "schemaVersion": "pxos-ops/1.0",
            "program": [
                {"op": "RECT", "x": 15, "y": 15, "w": 50, "h": 50, "r": 255, "g": 0, "b": 0},  # Different position
                {"op": "COMMIT"}
            ]
        }
        
        with open(sample_dir2 / "drifted.json", "w") as f:
            json.dump(drifted2, f, indent=2)
            
        with open(sample_dir2 / "path.txt", "w") as f:
            f.write("P1 -> P3 -> P5")
            
        with open(sample_dir2 / "seed.txt", "w") as f:
            f.write("67890")
    
    def open_scroll(self):
        """Open a selected scroll"""
        selection = self.scrolls_list.curselection()
        if selection:
            scroll_id = self.scrolls_list.get(selection[0])
            try:
                self.controller.open_scroll(scroll_id)
                self.update_metadata_display()
                # Show initial diff
                self.controller.render_diff()
            except FileNotFoundError:
                print(f"Scroll {scroll_id} not found")
    
    def replay_drift(self):
        """Replay the current drift"""
        self.controller.click_replay()
        self.update_metadata_display()
    
    def step_forward(self):
        """Step forward in the replay"""
        self.controller.step_forward()
        self.update_metadata_display()
    
    def step_back(self):
        """Step back in the replay"""
        self.controller.step_back()
        self.update_metadata_display()
    
    def update_metadata_display(self):
        """Update the metadata display"""
        if self.controller.current_scroll:
            metadata = f"""Path: {self.controller.current_scroll['path']}
Seed: {self.controller.current_scroll['seed']}
Step: {self.controller.current_step}
Status: {self.controller.current_scroll['status']}
"""
            self.metadata_text.delete(1.0, tk.END)
            self.metadata_text.insert(1.0, metadata)

if __name__ == "__main__":
    app = HallOfDriftVisualWorkbench()
    app.mainloop()