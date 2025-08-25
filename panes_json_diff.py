import tkinter as tk
from tkinter import scrolledtext
from typing import List, Tuple
from diff_models import JsonDiff

class TkJsonDiffPane:
    """Pane adapter for displaying JSON diffs with color-coded tags"""
    def __init__(self, widget: scrolledtext.ScrolledText):
        self.widget = widget
        self.widget.configure(state="normal")
        self.widget.tag_configure("same", foreground="green")
        self.widget.tag_configure("changed", foreground="orange")
        self.widget.tag_configure("added", foreground="red")
        self.widget.tag_configure("removed", foreground="red")

    def show_diff(self, diff: JsonDiff) -> None:
        """Display a JsonDiff object with color-coded tags"""
        self.widget.delete("1.0", "end")
        self.widget.insert("end", f"# Diff: same={diff.same_count} changed={diff.changed_count} "
                                 f"added={diff.added_count} removed={diff.removed_count}\n")
        for op_diff in diff.ops:
            if op_diff.status == "same":
                self.widget.insert("end", f"= [{op_diff.index}] {op_diff.op_left.get('op')}\n", "same")
            elif op_diff.status == "added":
                self.widget.insert("end", f"+ [{op_diff.index}] {op_diff.op_right.get('op')}\n", "added")
            elif op_diff.status == "removed":
                self.widget.insert("end", f"- [{op_diff.index}] {op_diff.op_left.get('op')}\n", "removed")
            else:  # changed
                self.widget.insert("end", f"~ [{op_diff.index}] {op_diff.op_left.get('op')}\n", "changed")
                for field_diff in op_diff.field_diffs:
                    self.widget.insert("end", f"  {field_diff.field}: {field_diff.left} → {field_diff.right}\n", "changed")
        self.widget.configure(state="disabled")
