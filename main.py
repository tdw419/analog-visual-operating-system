import tkinter as tk
from tkinter import scrolledtext, Button, ttk
import json
from pxos_sync_engine import PXOSEngine, Transforms, Profile
from adapters import TkTextPane, TkTilesPane, TkReplayPane
from hall_of_drift import HallOfDriftController, DriftStorage
from panes_json_diff import TkJsonDiffPane
from panes_overlay import TkOverlayPane
from pxos_lower_encode import lower_hlir_to_llir, encode_tiles, ecc_stats
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python

class PXOSWorkbench(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PXOS 6-Pane Workbench with Lineage Audit")
        self.geometry("2000x900")
        tr = Transforms()
        tr.T_py_to_hlir = T_py_to_hlir
        tr.T_analog_to_hlir = T_analog_to_hlir
        tr.T_hlir_to_analog = T_hlir_to_analog
        tr.validate_hlir = validate_hlir
        tr.lower_hlir_to_llir = lower_hlir_to_llir
        tr.encode_tiles = encode_tiles
        tr.ecc_stats = ecc_stats
        self.engine = PXOSEngine(tr, Profile(ecc="hamming16_12"))
        self.storage = DriftStorage()
        self.p1 = scrolledtext.ScrolledText(self)  # Placeholder for initialization
        self.p2 = scrolledtext.ScrolledText(self)
        self.p3 = scrolledtext.ScrolledText(self)
        self.p4 = scrolledtext.ScrolledText(self)
        self.p5 = scrolledtext.ScrolledText(self)
        self.p6 = tk.Canvas(self, width=300, height=300, bg="white")
        self.hall_controller = HallOfDriftController(self.engine, {
            "P1": TkTextPane("P1", self.p1),
            "P2": TkTextPane("P2", self.p2),
            "P3": TkTextPane("P3", self.p3),
            "P4": TkJsonDiffPane(self.p4),
            "P5": TkTextPane("P5", self.p5),
            "P6": TkOverlayPane(self.p6)
        }, self.storage)

        # Main paned window
        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True)

        # Workbench frame
        workbench_frame = tk.Frame(main_paned)
        main_paned.add(workbench_frame, weight=3)

        # Layout
        top = tk.Frame(workbench_frame)
        top.pack(fill="both", expand=True)
        bottom = tk.Frame(workbench_frame)
        bottom.pack(fill="both", expand=True)

        # Panes
        tk.Label(top, text="1. Python Source").grid(row=0, column=0, padx=5, pady=5)
        self.p1 = scrolledtext.ScrolledText(top, width=40, height=20)
        self.p1.grid(row=1, column=0, padx=5, pady=5)
        self.p1.insert("end", "import viewer_adapter as VA\nVA.RECT(20,20,40,20,64)\nVA.COMMIT()")
        Button(top, text="📌 Pin P1", command=lambda: self.toggle_pin("P1")).grid(row=2, column=0, padx=5, pady=5)

        tk.Label(top, text="2. Analog Text Mirror").grid(row=0, column=1, padx=5, pady=5)
        self.p2 = scrolledtext.ScrolledText(top, width=40, height=20)
        self.p2.grid(row=1, column=1, padx=5, pady=5)
        Button(top, text="📌 Pin P2", command=lambda: self.toggle_pin("P2")).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(top, text="3. Analog Source Editor").grid(row=0, column=2, padx=5, pady=5)
        self.p3 = scrolledtext.ScrolledText(top, width=40, height=20)
        self.p3.grid(row=1, column=2, padx=5, pady=5)
        Button(top, text="📌 Pin P3", command=lambda: self.toggle_pin("P3")).grid(row=2, column=2, padx=5, pady=5)

        tk.Label(bottom, text="4. Tile Sheet (JSON Diff)").grid(row=0, column=0, padx=5, pady=5)
        self.p4 = scrolledtext.ScrolledText(bottom, width=40, height=10)
        self.p4.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(bottom, text="5. HLIR JSON").grid(row=0, column=1, padx=5, pady=5)
        self.p5 = scrolledtext.ScrolledText(bottom, width=40, height=10)
        self.p5.grid(row=1, column=1, padx=5, pady=5)
        Button(bottom, text="📌 Pin P5", command=lambda: self.toggle_pin("P5")).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(bottom, text="6. Live Replay (Pixel Overlay)").grid(row=0, column=2, padx=5, pady=5)
        self.p6 = tk.Canvas(bottom, width=300, height=300, bg="white")
        self.p6.grid(row=1, column=2, padx=5, pady=5)

        # Lineage Audit Pane (P7)
        audit_frame = tk.Frame(main_paned)
        main_paned.add(audit_frame, weight=1)
        tk.Label(audit_frame, text="7. Lineage Audit", font=("Arial", 12, "bold")).pack(pady=5)
        self.audit_listbox = tk.Listbox(audit_frame, height=20)
        self.audit_listbox.pack(fill="both", expand=True)
        self.audit_listbox.bind("<<ListboxSelect>>", self.on_scroll_select)
        self.diff_mode_var = tk.StringVar(value="op_level")
        tk.OptionMenu(audit_frame, self.diff_mode_var, "op_level", "field_level", "render_overlay",
                      command=lambda _: self.hall_controller.set_diff_mode(self.diff_mode_var.get())).pack()
        Button(audit_frame, text="Replay", command=self.hall_controller.click_replay).pack(pady=2)
        Button(audit_frame, text="Step Forward", command=self.hall_controller.step_forward).pack(pady=2)
        Button(audit_frame, text="Step Back", command=self.hall_controller.step_back).pack(pady=2)
        self.annotation_text = tk.Text(audit_frame, height=2, width=40)
        self.annotation_text.pack(pady=2)
        Button(audit_frame, text="Bless", command=self.bless_scroll).pack(pady=2)
        Button(audit_frame, text="Export to Regression", command=self.hall_controller.export_scroll).pack(pady=2)
        Button(audit_frame, text="Back to Gallery", command=self.hall_controller.return_gallery).pack(pady=2)

        top.columnconfigure((0,1,2), weight=1)
        top.rowconfigure(1, weight=1)
        bottom.columnconfigure((0,1,2), weight=1)
        bottom.rowconfigure(1, weight=1)

        # Register panes
        self.hall_controller.panes["P1"] = TkTextPane("P1", self.p1)
        self.hall_controller.panes["P2"] = TkTextPane("P2", self.p2)
        self.hall_controller.panes["P3"] = TkTextPane("P3", self.p3)
        self.hall_controller.panes["P4"] = TkJsonDiffPane(self.p4)
        self.hall_controller.panes["P5"] = TkTextPane("P5", self.p5)
        self.hall_controller.panes["P6"] = TkOverlayPane(self.p6)
        for pane_id, pane in self.hall_controller.panes.items():
            self.engine.register(pane)

        # Initial sync and gallery render
        self.engine.on_edit("P1")
        self.hall_controller.render_gallery()

    def toggle_pin(self, pane_id: str) -> None:
        pane = self.engine.panes[pane_id]
        pane.pinned = not pane.pinned
        getattr(self, pane_id).configure(bg="lightyellow" if pane.pinned else "white")

    def on_scroll_select(self, event) -> None:
        selection = self.audit_listbox.curselection()
        if selection:
            scroll_id = self.audit_listbox.get(selection[0]).split(" ")[0]
            self.hall_controller.open_scroll(scroll_id)
            self.annotation_text.delete("1.0", tk.END)
            self.annotation_text.insert("1.0", self.hall_controller.current_scroll["annotation"])

    def bless_scroll(self) -> None:
        annotation = self.annotation_text.get("1.0", tk.END).strip()
        self.hall_controller.bless_scroll(annotation)
        self.hall_controller.render_gallery()

if __name__ == "__main__":
    PXOSWorkbench().mainloop()
