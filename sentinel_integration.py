# sentinel_integration.py - Integration of Lineage Sentinel into PXOS Workbench
import tkinter as tk
from tkinter import ttk, scrolledtext
import asyncio
import threading
from pathlib import Path
import json
import difflib

from lineage_sentinel import PXOSLineageSentinel
from pxos_sync_engine_enhanced import PXOSEngine

class SentinelPane(tk.Frame):
    """A PXOS pane that shows live sentinel status and controls"""
    
    def __init__(self, parent, engine: PXOSEngine):
        super().__init__(parent)
        self.engine = engine
        self.sentinel = PXOSLineageSentinel(engine)
        self.continuous_task = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        tk.Label(self, text="🛡️ Lineage Sentinel", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Status display
        self.status_var = tk.StringVar(value="Dormant")
        self.status_label = tk.Label(self, textvariable=self.status_var, fg="blue")
        self.status_label.pack(pady=2)
        
        # Controls frame
        controls = tk.Frame(self)
        controls.pack(pady=5)
        
        # Ritual buttons
        tk.Button(controls, text="Quick Ritual (25)", 
                 command=lambda: self.run_ritual(25)).pack(side="left", padx=2)
        tk.Button(controls, text="Deep Ritual (100)", 
                 command=lambda: self.run_ritual(100)).pack(side="left", padx=2)
        tk.Button(controls, text="Epic Ritual (500)", 
                 command=lambda: self.run_ritual(500)).pack(side="left", padx=2)
        
        # Continuous watch toggle
        self.watch_var = tk.BooleanVar()
        tk.Checkbutton(controls, text="Continuous Watch", variable=self.watch_var,
                      command=self.toggle_continuous_watch).pack(side="left", padx=5)
        
        # Results display
        self.results_text = scrolledtext.ScrolledText(self, height=8, width=60)
        self.results_text.pack(pady=5, fill="both", expand=True)
        
        # Hall of Drift access
        tk.Button(self, text="📜 Open Hall of Drift", 
                 command=self.open_hall_of_drift).pack(pady=2)
    
    def run_ritual(self, iterations: int):
        """Run a sentinel ritual asynchronously"""
        self.status_var.set(f"Running {iterations} trials...")
        self.results_text.insert(tk.END, f"\n🔮 Starting {iterations}-trial ritual...\n")
        
        # Run in thread to avoid blocking UI
        def ritual_thread():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the ritual
                report = loop.run_until_complete(
                    self.sentinel.guardian_ritual(iterations=iterations, verbose=False)
                )
                
                # Update UI from main thread
                self.after(0, lambda: self.display_ritual_results(report))
                
            except Exception as e:
                self.after(0, lambda: self.display_error(f"Ritual failed: {e}"))
        
        threading.Thread(target=ritual_thread, daemon=True).start()
    
    def display_ritual_results(self, report):
        """Display ritual results in the UI"""
        success_rate = report['success_rate']
        if success_rate == 1.0:
            status_color = "green"
            status_text = "✅ Perfect Lineage"
        elif success_rate >= 0.95:
            status_color = "orange" 
            status_text = f"⚠️ Minor Drift ({report['failures']} failures)"
        else:
            status_color = "red"
            status_text = f"❌ Significant Drift ({report['failures']} failures)"
            
        self.status_var.set(status_text)
        self.status_label.config(fg=status_color)
        
        result_text = f"""
Trials: {report['trials']}
Failures: {report['failures']}
Success Rate: {success_rate:.1%}
Duration: {report['duration_seconds']}s
Avg/Trial: {report['average_trial_time_ms']}ms
"""
        
        self.results_text.insert(tk.END, result_text)
        if report['failures'] > 0:
            self.results_text.insert(tk.END, f"Failed seeds: {report['failed_seeds']}\n")
        
        self.results_text.see(tk.END)
    
    def display_error(self, error_msg):
        """Display error in the UI"""
        self.status_var.set("Error")
        self.status_label.config(fg="red")
        self.results_text.insert(tk.END, f"❌ {error_msg}\n")
        self.results_text.see(tk.END)
    
    def toggle_continuous_watch(self):
        """Toggle continuous sentinel watch"""
        if self.watch_var.get():
            self.start_continuous_watch()
        else:
            self.stop_continuous_watch()
    
    def start_continuous_watch(self):
        """Start continuous background watching"""
        if self.continuous_task:
            return
            
        self.status_var.set("🔮 Watching...")
        self.status_label.config(fg="blue")
        
        async def watch_loop():
            while self.watch_var.get():
                try:
                    report = await self.sentinel.guardian_ritual(iterations=10, verbose=False)
                    self.after(0, lambda r=report: self.update_watch_status(r))
                    await asyncio.sleep(300)  # 5 minute intervals
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.after(0, lambda: self.display_error(f"Watch error: {e}"))
                    break
        
        def run_watch():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(watch_loop())
        
        self.continuous_task = threading.Thread(target=run_watch, daemon=True)
        self.continuous_task.start()
    
    def stop_continuous_watch(self):
        """Stop continuous watching"""
        if self.continuous_task:
            self.continuous_task = None
        self.status_var.set("Watch Stopped")
        self.status_label.config(fg="gray")
    
    def update_watch_status(self, report):
        """Update status from continuous watch"""
        if report['failures'] == 0:
            self.status_var.set("🛡️ Vigilant")
            self.status_label.config(fg="green")
        else:
            self.status_var.set(f"⚠️ {report['failures']} drifts detected")
            self.status_label.config(fg="orange")
    
    def open_hall_of_drift(self):
        """Open Hall of Drift browser"""
        hall_window = tk.Toplevel(self)
        hall_window.title("📜 Hall of Drift")
        hall_window.geometry("800x600")
        
        # List scrolls (failure files)
        scrolls_frame = tk.Frame(hall_window)
        scrolls_frame.pack(fill="both", expand=True)
        
        scrolls_list = tk.Listbox(scrolls_frame)
        scrolls_list.pack(side="left", fill="y")
        
        # Populate with .scroll files
        hall_path = self.sentinel.hall_of_drift
        scroll_files = list(hall_path.glob("*.scroll"))
        
        for scroll_file in scroll_files:
            scrolls_list.insert(tk.END, scroll_file.stem)
        
        # Scroll content display
        content_text = scrolledtext.ScrolledText(scrolls_frame)
        content_text.pack(side="right", fill="both", expand=True)
        
        def show_scroll_content(event):
            selection = scrolls_list.curselection()
            if selection:
                scroll_name = scrolls_list.get(selection[0])
                scroll_file = hall_path / f"{scroll_name}.scroll"
                if scroll_file.exists():
                    content = scroll_file.read_text()
                    content_text.delete(1.0, tk.END)
                    content_text.insert(1.0, content)
        
        scrolls_list.bind("<<ListboxSelect>>", show_scroll_content)

class DriftDiffPane(tk.Toplevel):
    """A specialized pane for visual HLIR drift comparison"""
    
    def __init__(self, parent, canonical_hlir, divergent_hlir, failure_path, seed):
        super().__init__(parent)
        self.title(f"🔍 Drift Analysis - Seed {seed}")
        self.geometry("1200x800")
        
        self.canonical_hlir = canonical_hlir
        self.divergent_hlir = divergent_hlir
        self.failure_path = failure_path
        self.seed = seed
        
        self.setup_ui()
        self.show_diff()
    
    def setup_ui(self):
        # Header with metadata
        header = tk.Frame(self)
        header.pack(fill="x", pady=5)
        
        tk.Label(header, text=f"Failure Path: {' → '.join(self.failure_path)}", 
                font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(header, text=f"Seed: {self.seed}", 
                font=("Arial", 10)).pack(side="right")
        
        # Main content frame
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left pane - Canonical HLIR
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        
        tk.Label(left_frame, text="✅ Canonical HLIR", 
                font=("Arial", 10, "bold"), fg="green").pack()
        self.canonical_text = scrolledtext.ScrolledText(left_frame, width=50, height=30)
        self.canonical_text.pack(fill="both", expand=True)
        
        # Right pane - Divergent HLIR
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        tk.Label(right_frame, text="❌ Divergent HLIR", 
                font=("Arial", 10, "bold"), fg="red").pack()
        self.divergent_text = scrolledtext.ScrolledText(right_frame, width=50, height=30)
        self.divergent_text.pack(fill="both", expand=True)
        
        # Controls
        controls = tk.Frame(self)
        controls.pack(fill="x", pady=5)
        
        tk.Button(controls, text="🔄 Replay", command=self.replay_drift).pack(side="left", padx=5)
        tk.Button(controls, text="📋 Copy Seed", command=self.copy_seed).pack(side="left", padx=5)
        tk.Button(controls, text="💾 Export", command=self.export_drift).pack(side="left", padx=5)
        tk.Button(controls, text="✅ Mark Reviewed", command=self.mark_reviewed).pack(side="right", padx=5)
    
    def show_diff(self):
        """Display the HLIR diff with highlighting"""
        canonical_json = json.dumps(self.canonical_hlir, indent=2, sort_keys=True)
        divergent_json = json.dumps(self.divergent_hlir, indent=2, sort_keys=True)
        
        # Insert content
        self.canonical_text.insert(tk.END, canonical_json)
        self.divergent_text.insert(tk.END, divergent_json)
        
        # Calculate and highlight differences
        canonical_lines = canonical_json.splitlines()
        divergent_lines = divergent_json.splitlines()
        
        differ = difflib.SequenceMatcher(None, canonical_lines, divergent_lines)
        
        # Configure tags for highlighting
        self.canonical_text.tag_configure("removed", background="misty rose")
        self.canonical_text.tag_configure("changed", background="light yellow")
        self.divergent_text.tag_configure("added", background="light green")
        self.divergent_text.tag_configure("changed", background="light yellow")
        
        # Apply highlighting based on diff
        for opcode, i1, i2, j1, j2 in differ.get_opcodes():
            if opcode == 'delete':
                # Highlight removed lines in canonical
                for line_no in range(i1, i2):
                    start = f"{line_no + 1}.0"
                    end = f"{line_no + 1}.end"
                    self.canonical_text.tag_add("removed", start, end)
            elif opcode == 'insert':
                # Highlight added lines in divergent
                for line_no in range(j1, j2):
                    start = f"{line_no + 1}.0"
                    end = f"{line_no + 1}.end"
                    self.divergent_text.tag_add("added", start, end)
            elif opcode == 'replace':
                # Highlight changed lines in both
                for line_no in range(i1, i2):
                    start = f"{line_no + 1}.0"
                    end = f"{line_no + 1}.end"
                    self.canonical_text.tag_add("changed", start, end)
                for line_no in range(j1, j2):
                    start = f"{line_no + 1}.0"
                    end = f"{line_no + 1}.end"
                    self.divergent_text.tag_add("changed", start, end)
    
    def replay_drift(self):
        """Replay the drift in the main PXOS workbench"""
        print(f"🔄 Replaying drift with seed {self.seed}...")
        # This would integrate with the main PXOS workbench to replay the failure
        pass
    
    def copy_seed(self):
        """Copy the seed to clipboard for manual reproduction"""
        self.clipboard_clear()
        self.clipboard_append(str(self.seed))
        print(f"📋 Copied seed {self.seed} to clipboard")
    
    def export_drift(self):
        """Export the drift data for regression testing"""
        export_data = {
            "seed": self.seed,
            "failure_path": self.failure_path,
            "canonical_hlir": self.canonical_hlir,
            "divergent_hlir": self.divergent_hlir,
            "timestamp": str(datetime.now())
        }
        
        filename = f"drift_export_{self.seed}.json"
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)
        
        print(f"💾 Exported drift to {filename}")
    
    def mark_reviewed(self):
        """Mark this drift as reviewed"""
        print(f"✅ Marked drift {self.seed} as reviewed")
        # This would update the Hall of Drift status
        self.destroy()

class EnhancedPXOSWorkbench(tk.Tk):
    """PXOS Workbench with integrated Lineage Sentinel"""
    
    def __init__(self):
        super().__init__()
        self.title("PXOS 6-Pane Workbench with Lineage Sentinel")
        self.geometry("2000x900")
        
        # Create your normal PXOS engine
        from pxos_sync_engine_enhanced import Transforms, Profile
        from transpiler import T_py_to_hlir
        from validate_hlir import validate_hlir
        from hlir_to_py import hlir_to_python
        
        tr = Transforms()
        tr.T_py_to_hlir = T_py_to_hlir
        tr.validate_hlir = validate_hlir
        # ... other transforms
        
        self.engine = PXOSEngine(tr, Profile())
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create main paned window
        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True)
        
        # Left side: Regular 6-pane workbench
        workbench_frame = tk.Frame(main_paned)
        main_paned.add(workbench_frame, weight=3)
        
        # TODO: Add your normal P1-P6 panes here
        tk.Label(workbench_frame, text="Regular PXOS Panes Here", 
                bg="lightgray").pack(fill="both", expand=True)
        
        # Right side: Sentinel pane
        sentinel_frame = tk.Frame(main_paned)
        main_paned.add(sentinel_frame, weight=1)
        
        self.sentinel_pane = SentinelPane(sentinel_frame, self.engine)
        self.sentinel_pane.pack(fill="both", expand=True)
    
    def show_drift_analysis(self, canonical_hlir, divergent_hlir, failure_path, seed):
        """Open the visual drift analysis pane"""
        DriftDiffPane(self, canonical_hlir, divergent_hlir, failure_path, seed)

if __name__ == "__main__":
    # Launch enhanced workbench
    app = EnhancedPXOSWorkbench()
    app.mainloop()