"""Create one safe ANSI splash asset from a versioned PNG at release build time.

Requires Pillow only on the release-authoring machine.  BULL itself reads the
resulting static base64 file and has no image-renderer runtime dependency.
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

from PIL import Image


def render(image: Image.Image, columns: int = 38, rows: int = 27) -> str:
    """Encode two vertical pixels per terminal cell with foreground/background."""
    image = image.convert('RGB').resize((columns, rows * 2), Image.Resampling.LANCZOS)
    lines: list[str] = []
    for y in range(0, rows * 2, 2):
        pieces: list[str] = []
        for x in range(columns):
            top = image.getpixel((x, y))
            bottom = image.getpixel((x, y + 1))
            pieces.append(
                f'\x1b[38;2;{top[0]};{top[1]};{top[2]};48;2;'
                f'{bottom[0]};{bottom[1]};{bottom[2]}m▀'
            )
        lines.append(''.join(pieces) + '\x1b[0m')
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--columns', type=int, default=38)
    parser.add_argument('--rows', type=int, default=27)
    args = parser.parse_args()
    if not 16 <= args.columns <= 64 or not 12 <= args.rows <= 34:
        raise SystemExit('columns must be 16..64 and rows must be 12..34')
    encoded = base64.b64encode(render(Image.open(args.source), args.columns, args.rows).encode('utf-8')).decode('ascii')
    args.destination.write_text(encoded + '\n', encoding='ascii')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
