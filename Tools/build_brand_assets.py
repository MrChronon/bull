"""Derive BULL release assets from the locked canonical logo without redrawing it."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "Assets" / "Brand"
MASTER = BRAND / "bull-logo-canonical.png"
LOCK = BRAND / "brand-lock.json"
VERSION = "v0.25.0.0"
EXPECTED_SHA256 = "60d91a700b9cd91ad3fd6ad598287a8e2cccd067f2ab0ed7515dd52af44b2269"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contain(image: Image.Image, size: tuple[int, int], padding: int = 0) -> Image.Image:
    available = (size[0] - 2 * padding, size[1] - 2 * padding)
    fitted = ImageOps.contain(image, available, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return canvas


def svg_wrapper(png_name: str, width: int, height: int, *, label: str) -> str:
    payload = base64.b64encode((BRAND / png_name).read_bytes()).decode("ascii")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">\n'
        f'  <image width="{width}" height="{height}" href="data:image/png;base64,{payload}"/>\n'
        '</svg>\n'
    )


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    actual = sha256(MASTER)
    if actual != EXPECTED_SHA256:
        raise RuntimeError(f"Canonical logo changed: {actual}")

    with Image.open(MASTER) as opened:
        master = opened.convert("RGBA")
    if master.size != (1774, 887):
        raise RuntimeError(f"Unexpected canonical dimensions: {master.size}")

    # These crops are recorded in brand-lock.json and change only by an explicit
    # brand decision. Pixels inside the crops remain untouched except resizing.
    logo = master.crop((31, 170, 1763, 718))
    wordmark = master.crop((47, 186, 1323, 702))
    mark_source = master.crop((1336, 248, 1731, 643))

    logo.save(BRAND / "bull-logo.png", optimize=True)
    wordmark.save(BRAND / "bull-wordmark.png", optimize=True)
    mark = contain(mark_source, (1024, 1024), padding=64)
    mark.save(BRAND / "bull-mark.png", optimize=True)

    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        contain(mark_source, (size, size), padding=max(1, round(size / 16))).save(
            BRAND / f"bull-mark-{size}.png", optimize=True
        )
    contain(mark_source, (32, 32), padding=2).save(BRAND / "favicon.png", optimize=True)

    on_light = Image.new("RGBA", (1024, 1024), "#F3F7F5")
    on_light.alpha_composite(mark)
    on_light.save(BRAND / "bull-mark-on-light.png", optimize=True)
    on_dark = Image.new("RGBA", (1024, 1024), "#07120F")
    on_dark.alpha_composite(mark)
    on_dark.save(BRAND / "bull-mark-on-dark.png", optimize=True)
    alpha = mark.getchannel("A")
    mono = Image.new("RGBA", mark.size, "#FFFFFF")
    mono.putalpha(alpha)
    mono.save(BRAND / "bull-mark-mono.png", optimize=True)

    (BRAND / "bull-logo-canonical.svg").write_text(
        svg_wrapper("bull-logo-canonical.png", 1774, 887, label="BULL canonical logo"), encoding="utf-8"
    )
    (BRAND / "bull-wordmark.svg").write_text(
        svg_wrapper("bull-wordmark.png", wordmark.width, wordmark.height, label="BULL wordmark"), encoding="utf-8"
    )
    (BRAND / "bull-mark.svg").write_text(
        svg_wrapper("bull-mark.png", 1024, 1024, label="BULL mark"), encoding="utf-8"
    )
    (BRAND / "bull-mark-light.svg").write_text(
        svg_wrapper("bull-mark-on-light.png", 1024, 1024, label="BULL mark on light background"), encoding="utf-8"
    )
    (BRAND / "bull-mark-mono.svg").write_text(
        svg_wrapper("bull-mark-mono.png", 1024, 1024, label="BULL monochrome mark"), encoding="utf-8"
    )

    contain(mark_source, (512, 512), padding=32).save(ROOT / f"BULL-{VERSION}.png", optimize=True)
    contain(mark_source, (256, 256), padding=16).save(
        ROOT / f"BULL-{VERSION}.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    (ROOT / f"BULL-{VERSION}.svg").write_text(
        svg_wrapper("bull-mark.png", 1024, 1024, label=f"BULL {VERSION}"), encoding="utf-8"
    )

    social = Image.new("RGBA", (1280, 640), "#07120F")
    social_logo = contain(logo, (1180, 420), padding=24)
    social.alpha_composite(social_logo, (50, 60))
    social.save(BRAND / "github-social-preview.png", optimize=True)

    lock = {
        "schema": "bull-brand-lock",
        "schema_version": 1,
        "decision": "canonical_logo_approved",
        "decision_date": "2026-09-26",
        "source_file": "bull-logo-canonical.png",
        "source_sha256": actual,
        "source_dimensions": [1774, 887],
        "derivation": "crop_resize_only_no_redraw",
        "crops": {
            "logo": [31, 170, 1763, 718],
            "wordmark": [47, 186, 1323, 702],
            "mark": [1336, 248, 1731, 643],
        },
    }
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
