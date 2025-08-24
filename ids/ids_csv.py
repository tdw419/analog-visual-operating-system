# ids_csv.py
import csv, time
from pathlib import Path

CSV_HEADER = ["frame","dt","op","x","y","w","h","r","g","b","intensity","text","id"]

class CSVSession:
    def __init__(self, out_path: str):
        self.out_path = Path(out_path)
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.f = self.out_path.open("w", newline="", encoding="utf-8")
        self.w = csv.writer(self.f)
        self.w.writerow(CSV_HEADER)
        self.frame = 0
        self._last_ts = time.perf_counter()

    def _dt(self):
        now = time.perf_counter()
        dt = now - self._last_ts
        self._last_ts = now
        return dt

    def write_rect(self, x, y, w, h, r, g, b, intensity=1.0):
        self.w.writerow([self.frame, 0.0, "RECT", x, y, w, h, r, g, b, intensity, "", ""])

    def write_text(self, x, y, r, g, b, text, intensity=1.0):
        self.w.writerow([self.frame, 0.0, "TEXT", x, y, "", "", r, g, b, intensity, text, ""])

    def write_click(self, x, y, id_=""):
        self.w.writerow([self.frame, 0.0, "CLICK", x, y, "", "", "", "", "", 1.0, "", id_])

    def commit(self):
        dt = self._dt()
        self.w.writerow([self.frame, dt, "COMMIT", "", "", "", "", "", "", "", "", "", ""])
        self.frame += 1

    def close(self):
        self.f.flush()
        self.f.close()
