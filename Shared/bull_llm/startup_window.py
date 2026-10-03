"""A small, optional desktop splash for BULL's mandatory startup gate.

The splash is deliberately a native, separate window rather than terminal art.
It consumes only the versioned, bundled PNG and the three truthful startup
stages supplied by ``run_startup_regression``.  If Windows GUI facilities are
unavailable, BULL still runs normally; the splash is presentation only.
"""

from __future__ import annotations

from pathlib import Path
import re


_ASSET_DIR = Path(__file__).resolve().parents[2] / "Assets" / "Brand"
_MAX_STAGE_LENGTH = 96


def splash_image_path(version: str) -> Path:
    """Return the exact versioned splash image without accepting a path."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "", str(version or ""))
    return _ASSET_DIR / f"splash-{safe}.png"


def _stage_label(stage: object) -> str:
    """Keep UI-only stage text bounded and free from control characters."""
    value = " ".join(str(stage or "").split())
    return value[:_MAX_STAGE_LENGTH] or "Starting verification"


def _progress(current: object, total: object) -> tuple[int, int, float]:
    try:
        maximum = max(1, int(total))
    except (TypeError, ValueError):
        maximum = 1
    try:
        completed = int(current)
    except (TypeError, ValueError):
        completed = 0
    completed = min(maximum, max(0, completed))
    return completed, maximum, completed / maximum


class _DesktopSplash:
    """Thin Tk wrapper kept private so startup can fail open, never fail closed."""

    def __init__(self, root, stage, bar, *, width: int):
        self._root = root
        self._stage = stage
        self._bar = bar
        self._width = width
        self._closed = False

    def update(self, stage: object, current: object, total: object) -> bool:
        if self._closed:
            return False
        completed, maximum, fraction = _progress(current, total)
        try:
            self._stage.configure(text=f"{_stage_label(stage)}  ·  {completed}/{maximum}")
            self._bar.coords("fill", 0, 0, round(self._width * fraction), 8)
            self._root.update_idletasks()
            self._root.update()
            return True
        except Exception:
            self._closed = True
            return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._root.destroy()
        except Exception:
            pass


def _create_window(version: str, stage: object, current: object, total: object):
    """Create a compact, borderless desktop window using stdlib Tk only."""
    image_path = splash_image_path(version)
    if not image_path.is_file():
        return None
    root = None
    try:
        import tkinter as tk

        root = tk.Tk()
        root.configure(bg="#090B0E")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-toolwindow", True)
        except Exception:
            pass

        image = tk.PhotoImage(file=str(image_path))
        divisor = max(1, (max(image.width(), image.height()) + 639) // 640)
        if divisor > 1:
            image = image.subsample(divisor, divisor)

        frame = tk.Frame(root, bg="#090B0E", highlightbackground="#FF3C52", highlightthickness=1)
        frame.pack(padx=1, pady=1)
        art = tk.Label(frame, image=image, bg="#090B0E", borderwidth=0)
        art.image = image  # Keep PhotoImage alive for the lifetime of the window.
        art.pack()

        panel = tk.Frame(frame, bg="#111820")
        panel.pack(fill="x")
        tk.Label(
            panel,
            text=f"BULL {version}  |  Benchmarking & Usage of Local LLMs",
            fg="#F4F7F5", bg="#111820", font=("Consolas", 10, "bold"), anchor="w",
        ).pack(fill="x", padx=16, pady=(11, 3))
        stage_label = tk.Label(
            panel, text="", fg="#B7C6C8", bg="#111820", font=("Consolas", 9), anchor="w"
        )
        stage_label.pack(fill="x", padx=16, pady=(0, 8))
        bar_width = max(300, image.width() - 32)
        canvas = tk.Canvas(panel, width=bar_width, height=8, bg="#26323A", highlightthickness=0)
        canvas.create_rectangle(0, 0, 0, 8, fill="#FF3C52", outline="", tags="fill")
        canvas.pack(padx=16, pady=(0, 14))

        root.update_idletasks()
        x = max(0, (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2)
        y = max(0, (root.winfo_screenheight() - root.winfo_reqheight()) // 2)
        root.geometry(f"+{x}+{y}")
        window = _DesktopSplash(root, stage_label, canvas, width=bar_width)
        window.update(stage, current, total)
        return window
    except Exception:
        try:
            root.destroy()
        except Exception:
            pass
        return None


def open_startup_window(version: str, stage: object = "Starting verification", current: object = 0, total: object = 3):
    """Open the optional desktop splash, returning ``None`` when unavailable."""
    return _create_window(version, stage, current, total)
