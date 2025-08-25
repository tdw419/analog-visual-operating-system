import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from diff_models import JsonDiff, OpDiff, FieldDiff
from diff_utils import json_diff, compute_overlay
from pxos_sync_engine import PXOSEngine
from hlir_to_py import hlir_to_python
from pxos_dsl import T_hlir_to_analog
from PIL import Image

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
        if self.current_scroll and self.current_step < len(self.current_scroll["path"].split(" -> ")) - 1:
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
        if self.current_scroll:
            self.storage.bless_scroll(self.current_scroll["id"], annotation)
            self.state = "BLESSED"
            self.render_detail_view()

    def export_scroll(self) -> None:
        if self.current_scroll:
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
            elif hasattr(pane, "show_diff"):
                pane.show_diff(JsonDiff(ops=[], same_count=0, changed_count=0, added_count=0, removed_count=0))
            elif hasattr(pane, "show_image"):
                pane.show_image(Image.new("RGB", (256, 256), "white"))
            if hasattr(pane, "clear_diagnostics"):
                pane.clear_diagnostics()

    def seed_first_origin(self) -> None:
        if not self.current_scroll:
            return
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
        if self.current_scroll:
            for i in range(1, step + 1):
                origin = self.current_scroll["path"].split(" -> ")[i]
                self.engine.on_edit(origin)

    def render_detail_view(self) -> None:
        if not self.current_scroll:
            return
        canonical = self.current_scroll["canonical"]
        drifted = self.current_scroll["drifted"]
        if self.diff_mode in ["op_level", "field_level"]:
            jd = json_diff(canonical, drifted)
            self.panes["P2"].write(json.dumps(canonical, indent=2), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
            if hasattr(self.panes["P4"], "show_diff"):
                self.panes["P4"].show_diff(jd)
            else:
                self.panes["P4"].write(json.dumps(drifted, indent=2), origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        elif self.diff_mode == "render_overlay":
            img = compute_overlay(canonical, drifted)
            if hasattr(self.panes["P4"], "show_image"):
                self.panes["P4"].show_image(img)
            else:
                self.panes["P4"].write("Render overlay (PIL image placeholder)", origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
        self.panes["P6"].write(f"Path: {self.current_scroll['path']}\nSeed: {self.current_scroll['seed']}\nStep: {self.current_step}",
                              origin="hall_of_drift", build_id=self.engine.bus.build_id + 1)
