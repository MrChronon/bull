"""A small, optional desktop splash for BULL's mandatory startup gate.

The splash is deliberately a native, separate window rather than terminal art.
It consumes only a theme-selected bundled PNG and the truthful startup
progress supplied by ``run_startup_regression``.  If Windows GUI facilities are
unavailable, BULL still runs normally; the splash is presentation only.
"""

from __future__ import annotations

from pathlib import Path
import re
import time


_ASSET_DIR = Path(__file__).resolve().parents[2] / "Assets" / "Brand"
_MAX_STAGE_LENGTH = 96
_MAX_DETAIL_LENGTH = 140
_MATRIX_ACCENTS = {
    'matrix_bright': '#36FF73',
    'matrix_balanced': '#2DDC69',
    'matrix_soft': '#26B05B',
}


def _splash_style(theme: str) -> dict[str, str]:
    """Canonical theme IDs only: never use a preference as an asset path."""
    accent = _MATRIX_ACCENTS.get(theme)
    return {
        'asset_prefix': 'splash-matrix' if accent else 'splash',
        'accent': accent or '#FF3C52',
        'background': '#090B0E',
        'panel': '#0C1711' if accent else '#111820',
        'muted': '#B5CBBF' if accent else '#B7C6C8',
        'text': '#F4F7F5',
        'track': '#20382A' if accent else '#26323A',
    }


def splash_image_path(version: str, theme: str = 'bull_red') -> Path:
    """Return the exact versioned splash image without accepting a path."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "", str(version or ""))
    prefix = _splash_style(theme)['asset_prefix']
    return _ASSET_DIR / f"{prefix}-{safe}.png"


def _stage_label(stage: object) -> str:
    """Keep UI-only stage text bounded and free from control characters."""
    value = " ".join(str(stage or "").split())
    return value[:_MAX_STAGE_LENGTH] or "Starting verification"


def _stage_parts(stage: object) -> tuple[str, str]:
    """Split a bounded, presentation-only stage into heading and detail.

    The startup gate supplies the detail itself; the splash never guesses a
    test name or invents a progress counter.
    """
    lines = [" ".join(line.split()) for line in str(stage or "").splitlines()]
    lines = [line for line in lines if line]
    heading = (lines[0] if lines else "Starting verification")[:_MAX_STAGE_LENGTH]
    detail = " ".join(lines[1:])[:_MAX_DETAIL_LENGTH]
    return heading, detail


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


class _MatrixRain:
    """A bounded, optional right-edge layer; never uses benchmark RNG/state.

    Only 45 text items and one Tk-owned timer are reused. All drawing stays in
    the artwork canvas, separate from the authoritative progress panel.
    """

    _GLYPHS = '0123456789@#$%&*+=<>'

    def __init__(self, root, canvas, *, width: int, height: int, accent: str):
        self._root, self._canvas = root, canvas
        self._width, self._height = width, height
        self._started = time.monotonic()
        self._timer = None
        self._closed = False
        rgb = tuple(int(accent[i:i+2], 16) for i in (1, 3, 5))
        self._colours = [accent] + [
            '#' + ''.join(f'{round(channel * (0.72 - tail * .065)):02X}' for channel in rgb)
            for tail in range(8)
        ]
        self._items = [canvas.create_text(
            0, 0, text='', fill=accent, font=('Consolas', -max(10, width // 57)),
            anchor='center', state='hidden', tags='matrix-rain',
        ) for _ in range(45)]
        self._draw(0)
        self._timer = root.after(100, self._tick)

    def _draw(self, elapsed: float) -> None:
        spacing = max(12, self._height * .022)
        for column in range(5):
            x = round(self._width * (.907 + column * .016))
            speed = self._height * (.11 + column * .015)
            head = (elapsed * speed + column * self._height * .27) % (self._height + spacing * 9)
            for tail in range(9):
                y = head - tail * spacing
                item = self._items[column * 9 + tail]
                glyph = self._GLYPHS[(int(elapsed * 8) + column * 13 + tail * 7) % len(self._GLYPHS)]
                self._canvas.coords(item, x, y)
                self._canvas.itemconfigure(
                    item, text=glyph, fill=self._colours[tail],
                    state='normal' if self._height * .04 <= y <= self._height * .94 else 'hidden',
                )

    def _cancel_timer(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            try:
                self._root.after_cancel(timer)
            except Exception:
                pass

    def _tick(self) -> None:
        if self._closed:
            return
        self._cancel_timer()
        try:
            self._draw(max(0, time.monotonic() - self._started))
            self._timer = self._root.after(100, self._tick)
        except Exception:
            self.close()  # Animation failure must not fail verification.

    def close(self) -> None:
        self._closed = True
        self._cancel_timer()


class _DesktopSplash:
    """Thin Tk wrapper kept private so startup can fail open, never fail closed."""

    def __init__(self, root, stage, detail, bar, *, width: int, rain=None):
        self._root = root
        self._stage = stage
        self._detail = detail
        self._bar = bar
        self._width = width
        self._rain = rain
        self._closed = False

    def update(self, stage: object, current: object, total: object) -> bool:
        if self._closed:
            return False
        completed, maximum, fraction = _progress(current, total)
        try:
            heading, detail = _stage_parts(stage)
            self._stage.configure(text=f"{heading}  ·  {fraction:.0%} ({completed}/{maximum})")
            self._detail.configure(text=detail)
            self._bar.coords("fill", 0, 0, round(self._width * fraction), 8)
            return self.pump()
        except Exception:
            self.close()
            return False

    def pump(self) -> bool:
        """Process GUI events while a check is quiet, without advancing progress."""
        if self._closed:
            return False
        try:
            self._root.update_idletasks()
            self._root.update()
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._rain is not None:
            self._rain.close()
        try:
            self._root.destroy()
        except Exception:
            pass


def _create_window(version: str, stage: object, current: object, total: object, *, theme: str = 'bull_red'):
    """Create a compact, borderless desktop window using stdlib Tk only."""
    style = _splash_style(theme)
    image_path = splash_image_path(version, theme)
    if not image_path.is_file():
        return None
    root = None
    try:
        import tkinter as tk

        root = tk.Tk()
        root.configure(bg=style['background'])
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

        frame = tk.Frame(root, bg=style['background'], highlightbackground=style['accent'], highlightthickness=1)
        frame.pack(padx=1, pady=1)
        matrix_theme = theme in _MATRIX_ACCENTS
        if matrix_theme:
            art = tk.Canvas(frame, width=image.width(), height=image.height(),
                            bg=style['background'], highlightthickness=0)
            art.create_image(0, 0, anchor='nw', image=image)
        else:
            art = tk.Label(frame, image=image, bg=style['background'], borderwidth=0)
        art.image = image  # Keep PhotoImage alive for the lifetime of the window.
        art.pack()

        panel = tk.Frame(frame, bg=style['panel'])
        panel.pack(fill="x")
        tk.Label(
            panel,
            text=f"BULL {version}",
            fg=style['text'], bg=style['panel'], font=("Segoe UI", 14, "bold"), anchor="w",
            wraplength=image.width()-32,
        ).pack(fill="x", padx=16, pady=(11, 3))
        stage_label = tk.Label(
            panel, text="", fg=style['muted'], bg=style['panel'], font=("Segoe UI", 10), anchor="w", wraplength=image.width()-32
        )
        stage_label.pack(fill="x", padx=16, pady=(0, 2))
        detail_label = tk.Label(
            panel, text="", fg=style['text'], bg=style['panel'], font=("Segoe UI", 10), anchor="w", wraplength=image.width()-32
        )
        detail_label.pack(fill="x", padx=16, pady=(0, 8))
        bar_width = max(300, image.width() - 32)
        canvas = tk.Canvas(panel, width=bar_width, height=8, bg=style['track'], highlightthickness=0)
        canvas.create_rectangle(0, 0, 0, 8, fill=style['accent'], outline="", tags="fill")
        canvas.pack(padx=16, pady=(0, 14))

        root.update_idletasks()
        x = max(0, (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2)
        y = max(0, (root.winfo_screenheight() - root.winfo_reqheight()) // 2)
        root.geometry(f"+{x}+{y}")
        window = _DesktopSplash(root, stage_label, detail_label, canvas, width=bar_width)
        if matrix_theme:
            try:
                window._rain = _MatrixRain(root, art, width=image.width(), height=image.height(), accent=style['accent'])
            except Exception:
                art.delete('matrix-rain')  # Keep static artwork/progress if animation is unavailable.
        window.update(stage, current, total)
        return window
    except Exception:
        try:
            root.destroy()
        except Exception:
            pass
        return None


def open_startup_window(version: str, stage: object = "Starting verification", current: object = 0, total: object = 3, *, theme: str = 'bull_red'):
    """Open the optional desktop splash, returning ``None`` when unavailable."""
    return _create_window(version, stage, current, total, theme=theme)
