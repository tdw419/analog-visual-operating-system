# hall_of_drift.py
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from difflib import Differ
from pxos_sync_engine_enhanced import PXOSEngine
from hlir_to_py import hlir_to_python
from pxos_dsl import T_hlir_to_analog
from PIL import Image, ImageDraw
from json_diff import compute_json_diff, compute_field_level_diff
from pixel_overlay import compute_pixel_overlay
from visual_diff_ui import TkJsonDiffPane, TkOverlayPane, DiffModeSelector

class DriftStorage:
    """Manages storage and retrieval of drift scrolls in hall_of_drift/"""
    def __init__(self, base_path: Path = Path("hall_of_drift")):
        self.base_path = base_path
        self.base_path.mkdir(exist_ok=True)
        self.blessed_path = base_path / "blessed"
        self.blessed_path.mkdir(exist_ok=True)

    def list_scrolls(self) -> List[Dict[str, Any]]:
        scrolls = []
        for folder in self.base_path.glob("drift_*"):
            if folder.is_dir() and (folder / "canonical.json").exists():
                try:
                    with open(folder / "canonical.json") as f:
                        canonical = json.load(f)
                    with open(folder / "drifted.json") as f:
                        drifted = json.load(f)
                    with open(folder / "path.txt") as f:
                        path = f.read().strip()
                    with open(folder / "seed.txt") as f:
                        seed = int(f.read().strip())
                    annotation = (folder / "annotation.txt").read_text() if (folder / "annotation.txt").exists() else ""
                    scrolls.append({
                        "id": folder.name,
                        "canonical": canonical,
                        "drifted": drifted,
                        "path": path,
                        "seed": seed,
                        "status": "Blessed" if (self.blessed_path / folder.name).exists() else "Unreviewed",
                        "annotation": annotation
                    })
                except Exception:
                    continue
        return scrolls

    def load_scroll(self, scroll_id: str) -> Dict[str, Any]:
        folder = self.base_path / scroll_id
        if not folder.exists():
            raise FileNotFoundError(f"Scroll {scroll_id} not found")
        with open(folder / "canonical.json") as f:
            canonical = json.load(f)
        with open(folder / "drifted.json") as f:
            drifted = json.load(f)
        with open(folder / "path.txt") as f:
            path = f.read().strip()
        with open(folder / "seed.txt") as f:
            seed = int(f.read().strip())
        annotation = (folder / "annotation.txt").read_text() if (folder / "annotation.txt").exists() else ""
        return {
            "id": scroll_id,
            "canonical": canonical,
            "drifted": drifted,
            "path": path,
            "seed": seed,
            "status": "Blessed" if (self.blessed_path / scroll_id).exists() else "Unreviewed",
            "annotation": annotation
        }

    def bless_scroll(self, scroll_id: str, annotation: str) -> None:
        folder = self.base_path / scroll_id
        if not folder.exists():
            raise FileNotFoundError(f"Scroll {scroll_id} not found")
        with open(folder / "annotation.txt", "w") as f:
            f.write(annotation)
        os.rename(folder, self.blessed_path / scroll_id)

    def export_to_regression(self, scroll: Dict[str, Any]) -> None:
        regression_path = self.base_path / "regression_tests"
        regression_path.mkdir(exist_ok=True)
        test_id = f"test_{scroll['id']}"
        with open(regression_path / f"{test_id}.json", "w") as f:
            json.dump({
                "canonical": scroll["canonical"],
                "path": scroll["path"],
                "seed": scroll["seed"]
            }, f, indent=2)

class HallOfDriftController:
    """Manages the Hall of Drift UI and replay ritual in PXOS"""
    def __init__(self, engine: PXOSEngine, panes: Dict[str, Any], storage: DriftStorage):
        self.engine = engine
        self.panes = panes
        self.storage = storage
        self.state = "GALLERY_VIEW"
        self.current_scroll = None
        self.current_step = 0
        self.diff_mode = "op_level"  # op_level, field_level, render_overlay
        
        # Initialize visual diff components if they exist in panes
        if "P4" in self.panes and hasattr(self.panes["P4"], "show_diff"):
            self.json_diff_pane = self.panes["P4"]
        else:
            self.json_diff_pane = None
            
        if "P6" in self.panes and hasattr(self.panes["P6"], "show_overlay"):
            self.overlay_pane = self.panes["P6"]
        else:
            self.overlay_pane = None

    def open_scroll(self, scroll_id: str) -> None:
        self.current_scroll = self.storage.load_scroll(scroll_id)
        self.state = "DETAIL_VIEW"
        self.render_detail_view()

    def click_replay(self) -> None:
        self.state = "REPLAY_INIT"
        self.current_step = 0
        self.clear_all_panes()
        self.seed_first_origin()
        self.state = "REPLAY_STEP"
        self.render_diff()

    def step_forward(self) -> None:
        if self.current_step < len(self.current_scroll["path"].split(" -> ")) - 1:
            self.current_step += 1
            origin = self.current_scroll["path"].split(" -> ")[self.current_step]
            self.engine.on_edit(origin)
            self.render_diff()
            if self.current_step == len(self.current_scroll["path"].split(" -> ")) - 1:
                self.state = "REPLAY_COMPLETE"

    def step_back(self) -> None:
        if self.current_step > 0:
            self.current_step -= 1
            self.replay_up_to_step(self.current_step)
            self.render_diff()

    def bless_scroll(self, annotation: str) -> None:
        self.storage.bless_scroll(self.current_scroll["id"], annotation)
        self.state = "BLESSED"
        self.render_detail_view()

    def export_scroll(self) -> None:
        self.storage.export_to_regression(self.current_scroll)
        self.state = "EXPORTED"
        self.render_detail_view()

    def return_gallery(self) -> None:
        self.state = "GALLERY_VIEW"
        self.render_gallery()

    def set_diff_mode(self, mode: str) -> None:
        self.diff_mode = mode
        self.render_diff()

    def clear_all_panes(self) -> None:
        for pane in self.panes.values():
            if hasattr(pane, "write"):
                pane.write("", origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
            if hasattr(pane, "clear_diagnostics"):
                pane.clear_diagnostics()

    def seed_first_origin(self) -> None:
        first = self.current_scroll["path"].split(" -> ")[0]
        canonical = self.current_scroll["canonical"]
        if first == "P1":
            self.panes["P1"].write(hlir_to_python(canonical), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        elif first == "P3":
            self.panes["P3"].write(T_hlir_to_analog(canonical), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        else:
            self.panes["P5"].write(json.dumps(canonical), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        self.engine.on_edit(first)

    def replay_up_to_step(self, step: int) -> None:
        self.clear_all_panes()
        self.seed_first_origin()
        for i in range(1, step + 1):
            origin = self.current_scroll["path"].split(" -> ")[i]
            self.engine.on_edit(origin)

    def compute_json_diff(self, canonical: Dict[str, Any], drifted: Dict[str, Any]) -> str:
        d = Differ()
        canonical_lines = json.dumps(canonical, indent=2).splitlines()
        drifted_lines = json.dumps(drifted, indent=2).splitlines()
        diff = list(d.compare(canonical_lines, drifted_lines))
        if self.diff_mode == "op_level":
            return "\n".join(line for line in diff if '"op":' in line or line.startswith(('- ', '+ ')))
        elif self.diff_mode == "field_level":
            return "\n".join(line for line in diff if line.startswith(('- ', '+ ')))
        return "\n".join(diff)

    def compute_render_overlay(self, canonical: Dict[str, Any], drifted: Dict[str, Any]) -> Image.Image:
        img = Image.new("RGB", (256, 256), "white")
        draw = ImageDraw.Draw(img)
        for op_c, op_d in zip(canonical.get("program", []), drifted.get("program", [])):
            if op_c.get("op") == "RECT" and op_d.get("op") == "RECT":
                if op_c != op_d:
                    x, y, w, h = op_c["x"], op_c["y"], op_c["w"], op_c["h"]
                    draw.rectangle((x, y, x+w, y+h), outline="red", width=2)
        return img

    def render_diff(self):
        """Render the appropriate diff based on the current diff mode"""
        if not self.current_scroll:
            return
            
        canonical = self.current_scroll["canonical"]
        current = self.engine.cache.last_good_hlir

        if self.diff_mode == "op_level":
            # Render JSON diff in P4
            diff_result = compute_json_diff(canonical, current)
            if self.json_diff_pane:
                self.json_diff_pane.show_diff(diff_result)
            else:
                diff_text = "\n".join([f"{line_type}: {line}" for line_type, line in diff_result])
                self.panes["P4"].write(diff_text, origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        elif self.diff_mode == "field_level":
            # Render field-level diff in P4
            field_diff = compute_field_level_diff(canonical, current)
            if self.json_diff_pane:
                # Format field-level diff for display
                formatted_diff = []
                for op_type in ["added_ops", "removed_ops"]:
                    for op in field_diff[op_type]:
                        formatted_diff.append(("added" if op_type == "added_ops" else "removed", json.dumps(op)))
                for mod_op in field_diff["modified_ops"]:
                    formatted_diff.append(("changed", f"Modified operation at index {mod_op['index']}"))
                    for diff in mod_op["differences"]:
                        formatted_diff.append(("changed", f"  {diff['field']}: {diff['canonical']} -> {diff['current']}"))
                self.json_diff_pane.show_diff(formatted_diff)
            else:
                self.panes["P4"].write(json.dumps(field_diff, indent=2), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        elif self.diff_mode == "render_overlay":
            # Render pixel overlay in P6
            overlay_img = compute_pixel_overlay(canonical, current)
            if self.overlay_pane:
                self.overlay_pane.show_overlay(overlay_img)
            else:
                # For now, we'll just indicate that an overlay was computed
                # In a full implementation, this would display the image in the pane
                self.panes["P6"].write("Pixel overlay computed (implementation needed for full display)", 
                                      origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)

    def render_detail_view(self) -> None:
        if not self.current_scroll:
            return
            
        canonical = self.current_scroll["canonical"]
        drifted = self.current_scroll["drifted"]
        if self.diff_mode in ["op_level", "field_level"]:
            self.panes["P2"].write(self.compute_json_diff(canonical, drifted), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
            diff_result = compute_json_diff(canonical, drifted)
            if self.json_diff_pane and hasattr(self.json_diff_pane, "show_diff"):
                self.json_diff_pane.show_diff(diff_result)
            else:
                self.panes["P4"].write(json.dumps(drifted, indent=2), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        elif self.diff_mode == "render_overlay":
            img = self.compute_render_overlay(canonical, drifted)
            if self.overlay_pane and hasattr(self.overlay_pane, "show_overlay"):
                # Use the actual pixel overlay computation
                overlay_img = compute_pixel_overlay(canonical, drifted)
                self.overlay_pane.show_overlay(overlay_img)
            else:
                # Requires Tkinter PIL integration (PhotoImage)
                self.panes["P4"].write("Render overlay (PIL image placeholder)", origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        # Update P6 with metadata if it's not the overlay pane
        if not (self.overlay_pane and hasattr(self.overlay_pane, "show_overlay")):
            self.panes["P6"].write(f"Path: {self.current_scroll['path']}\nSeed: {self.current_scroll['seed']}\nStep: {self.current_step}", 
                                  origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)

    def render_gallery(self) -> None:
        scrolls = self.storage.list_scrolls()
        gallery_text = "\n".join(f"{s['id']} ({s['status']}): {s['path']} (Seed: {s['seed']})" for s in scrolls)
        self.panes["P2"].write(f"Gallery: {len(scrolls)} drift scrolls\n\n{gallery_text}", origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)