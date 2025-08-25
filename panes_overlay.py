import tkinter as tk
from PIL import Image, ImageTk
from typing import Optional

class TkOverlayPane:
    """Pane adapter for displaying pixel-level diff overlays"""
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._img_id: Optional[int] = None
        self.canvas.bind("<Configure>", self._on_resize)

    def show_image(self, img: Image.Image) -> None:
        """Display a PIL Image as a pixel diff overlay"""
        self._photo = ImageTk.PhotoImage(img)
        w = self.canvas.winfo_width() or self._photo.width()
        h = self.canvas.winfo_height() or self._photo.height()
        self.canvas.delete("all")
        self._img_id = self.canvas.create_image(w // 2, h // 2, image=self._photo, anchor="center")

    def _on_resize(self, event: tk.Event) -> None:
        """Recenter image on canvas resize"""
        if self._photo and self._img_id:
            self.canvas.delete(self._img_id)
            self._img_id = self.canvas.create_image(event.width // 2, event.height // 2, image=self._photo, anchor="center")
