import tkinter as tk
from tkinter import scrolledtext
import asyncio
import json

# Make sure the imports are correct now
from pxos_sync_engine import PXOSEngine, Transforms, Profile, ValidationError, Pane
from transpiler import T_py_to_hlir
from pxos_dsl import T_analog_to_hlir, T_hlir_to_analog
from validate_hlir import validate_hlir
from hlir_to_py import hlir_to_python

class TkTextPane(Pane):
    def __init__(self, pane_id, widget):
        self.id = pane_id
        self.widget = widget
        self.pinned = False
        self.last_build_id = -1
        self.last_origin = None

    def read(self) -> str:
        return self.widget.get("1.0", 'end-1c')

    def write(self, text: str, *, origin: str, build_id: int) -> None:
        if origin == self.id and build_id == self.last_build_id:
            print(f"Echo guard triggered for {self.id}")
            return

        print(f"Updating pane {self.id} from origin '{origin}' (Build #{build_id})")
        self.last_build_id = build_id
        self.last_origin = origin

        current_pos = self.widget.index(tk.INSERT)
        self.widget.delete("1.0", tk.END)
        self.widget.insert("1.0", text)
        self.widget.mark_set(tk.INSERT, current_pos)

    def annotate(self, message: str, *, severity: str = "error") -> None:
        print(f"ANNOTATE {self.id}: [{severity.upper()}] {message}")
        self.widget.tag_remove("error", "1.0", tk.END)
        self.widget.tag_remove("warn", "1.0", tk.END)
        self.widget.tag_add(severity, "1.0", "end")
        self.widget.tag_config(severity, foreground="red" if severity == "error" else "orange")


    def clear_diagnostics(self) -> None:
        self.widget.tag_remove("error", "1.0", tk.END)
        self.widget.tag_remove("warn", "1.0", tk.END)


class App(tk.Tk):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.title("Two-Pane Prototype")
        self.geometry("1200x700")

        # Core components
        tr = Transforms()
        tr.T_py_to_hlir = T_py_to_hlir
        tr.T_analog_to_hlir = T_analog_to_hlir
        tr.T_hlir_to_analog = T_hlir_to_analog
        tr.validate_hlir = validate_hlir
        # Add dummy implementations for the rest of the transforms
        tr.lower_hlir_to_llir = lambda h: []
        tr.encode_tiles = lambda llir, ecc: []
        tr.ecc_stats = lambda tiles: {}

        self.engine = PXOSEngine(tr, Profile(), loop=self.loop)

        self._create_widgets()

        # Start the tkinter mainloop integration with asyncio
        self.loop.create_task(self.tk_loop())

    async def tk_loop(self):
        while True:
            try:
                self.update()
                self.update_idletasks()
            except tk.TclError:
                print("Tkinter main window closed. Shutting down.")
                break
            await asyncio.sleep(0.01)

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Pane 1: Python Source
        tk.Label(self, text="Pane 1: Python Source (Editable)").grid(row=0, column=0, padx=5, pady=5)
        self.p1_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, width=60, height=30)
        self.p1_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.p1_text.bind("<KeyRelease>", lambda event: self.engine.on_edit("P1"))
        self.p1_text.insert("1.0", "RECT(10,10,20,20,128)")

        # Pane 2: Analog DSL
        tk.Label(self, text="Pane 2: Analog DSL (Editable)").grid(row=0, column=1, padx=5, pady=5)
        self.p2_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, width=60, height=30)
        self.p2_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.p2_text.bind("<KeyRelease>", lambda event: self.engine.on_edit("P2"))

        # Create and register pane adapters
        p1_adapter = TkTextPane("P1", self.p1_text)
        p2_adapter = TkTextPane("P2", self.p2_text)
        self.engine.register(p1_adapter)
        self.engine.register(p2_adapter)

        # Initial sync
        self.engine.on_edit("P1")


if __name__ == "__main__":
    print("Starting 2-pane prototype...")
    # This will fail in a headless environment, but we can check if it runs up to the point of failure.
    # The goal is to see the print statements from the engine logic.
    try:
        loop = asyncio.get_event_loop()
        app = App(loop)
        # We can't run loop.run_forever() in a script like this easily with tkinter.
        # The tk_loop coroutine will run the main loop.
        # To make it exit after a short time for testing:
        async def main():
            await app.tk_loop()

        # Run for a short duration to test logic, then exit
        loop.run_until_complete(asyncio.wait_for(main(), timeout=2.0))

    except tk.TclError as e:
        print(f"Tkinter TclError (expected in headless env): {e}")
    except Exception as e:
        print(f"Application exited with unexpected error: {e}")

    print("Prototype finished.")
