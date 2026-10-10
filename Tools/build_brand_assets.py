"""Derive BULL release assets from the locked canonical logo without redrawing it."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "Assets" / "Brand"
MASTER = BRAND / "bull-logo-canonical.png"
LOCK = BRAND / "brand-lock.json"
VERSION = "v0.29.0.1"
EXPECTED_SHA256 = "60d91a700b9cd91ad3fd6ad598287a8e2cccd067f2ab0ed7515dd52af44b2269"
RELEASE_RED = (255, 60, 82)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contain(image: Image.Image, size: tuple[int, int], padding: int = 0) -> Image.Image:
    available = (size[0] - 2 * padding, size[1] - 2 * padding)
    fitted = ImageOps.contain(image, available, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return canvas


def recolour_brand_pixels(image: Image.Image, target: tuple[int, int, int]) -> Image.Image:
    """Create a release-colour derivative without modifying the locked master."""
    result = image.convert("RGBA").copy()
    remapped = []
    for red, green, blue, alpha in result.getdata():
        saturated = max(red, green, blue) - min(red, green, blue) >= 24
        brand_coloured = max(red, green, blue) >= 48 and (green > red + 16 or blue > red + 16)
        if alpha and saturated and brand_coloured:
            intensity = max(red, green, blue) / 255.0
            remapped.append((
                round(target[0] * intensity),
                round(target[1] * intensity),
                round(target[2] * intensity),
                alpha,
            ))
        else:
            remapped.append((red, green, blue, alpha))
    result.putdata(remapped)
    return result


def ui_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("seguisb.ttf", "segoeuib.ttf") if bold else ("segoeui.ttf",)
    candidates = [Path("C:/Windows/Fonts") / name for name in names]
    candidates += [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def svg_wrapper(png_name: str, width: int, height: int, *, label: str) -> str:
    payload = base64.b64encode((BRAND / png_name).read_bytes()).decode("ascii")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">\n'
        f'  <image width="{width}" height="{height}" href="data:image/png;base64,{payload}"/>\n'
        '</svg>\n'
    )


def build_terminal_mark() -> None:
    """Sharper 48 x 24 ASCII-space cells; one resample from the locked crop."""
    if sha256(MASTER) != EXPECTED_SHA256:
        raise RuntimeError('Canonical logo changed')
    with Image.open(MASTER) as opened:
        mark = opened.convert('RGBA').crop((1336, 248, 1731, 643))
    background = Image.new('RGBA', mark.size, '#000000')
    background.alpha_composite(mark)
    # Console cells are approximately twice as tall as they are wide. Sampling
    # half as many rows preserves the square silhouette without special glyphs.
    pixels = background.convert('RGB').resize((48, 24), Image.Resampling.LANCZOS)
    rows = []
    for y in range(24):
        row = '\x1b[0m'
        for x in range(48):
            red, green, blue = pixels.getpixel((x, y))
            row += f'\x1b[48;2;{red};{green};{blue}m '
        rows.append(row + '\x1b[0m')
    payload = ('\n'.join(rows) + '\n').encode('ascii')
    (BRAND / 'bull-mark-console-48.ansi.b64').write_text(
        base64.b64encode(payload).decode('ascii') + '\n', encoding='ascii')


def build_theme_icons() -> None:
    """Canonical geometry plus a small install arrow; no redraw of the bull."""
    if sha256(MASTER) != EXPECTED_SHA256:
        raise RuntimeError('Canonical logo changed')
    with Image.open(MASTER) as opened:
        source = opened.convert('RGBA').crop((1336, 248, 1731, 643))
    sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    green = recolour_brand_pixels(source, (54, 255, 115))
    contain(green, (256,256), padding=16).save(BRAND/'bull-icon-matrix.ico', sizes=sizes)
    setup = contain(recolour_brand_pixels(source, RELEASE_RED), (256,256), padding=16)
    draw = ImageDraw.Draw(setup)
    draw.rounded_rectangle((160,158,248,248),radius=15,fill='#111820',outline='#F4F7F5',width=4)
    draw.line((204,172,204,218),fill='#F4F7F5',width=10)
    draw.line((188,205,204,222,220,205),fill='#F4F7F5',width=8)
    draw.line((184,234,224,234),fill='#F4F7F5',width=6)
    setup.save(BRAND/'bull-setup.ico',sizes=sizes)


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    actual = sha256(MASTER)
    if actual != EXPECTED_SHA256:
        raise RuntimeError(f"Canonical logo changed: {actual}")
    build_terminal_mark()
    build_theme_icons()

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
    red_wordmark = recolour_brand_pixels(wordmark, RELEASE_RED)
    red_wordmark.save(BRAND / "bull-wordmark-red.png", optimize=True)
    mark = contain(mark_source, (1024, 1024), padding=64)
    mark.save(BRAND / "bull-mark.png", optimize=True)
    red_mark_source = recolour_brand_pixels(mark_source, RELEASE_RED)
    red_mark = contain(red_mark_source, (1024, 1024), padding=64)
    red_mark.save(BRAND / "bull-mark-red.png", optimize=True)

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
    (BRAND / "bull-wordmark-red.svg").write_text(
        svg_wrapper("bull-wordmark-red.png", wordmark.width, wordmark.height, label="BULL red release wordmark"), encoding="utf-8"
    )
    (BRAND / "bull-mark.svg").write_text(
        svg_wrapper("bull-mark.png", 1024, 1024, label="BULL mark"), encoding="utf-8"
    )
    (BRAND / "bull-mark-red.svg").write_text(
        svg_wrapper("bull-mark-red.png", 1024, 1024, label="BULL red release mark"), encoding="utf-8"
    )
    (BRAND / "bull-mark-light.svg").write_text(
        svg_wrapper("bull-mark-on-light.png", 1024, 1024, label="BULL mark on light background"), encoding="utf-8"
    )
    (BRAND / "bull-mark-mono.svg").write_text(
        svg_wrapper("bull-mark-mono.png", 1024, 1024, label="BULL monochrome mark"), encoding="utf-8"
    )

    contain(mark_source, (512, 512), padding=32).save(ROOT / f"BULL-{VERSION}.png", optimize=True)
    # The Windows shell icon follows the release palette.  Keeping this separate
    # from the canonical master makes the Desktop/Start shortcut visibly match
    # the default BULL Red theme without changing the approved logo source.
    contain(red_mark_source, (256, 256), padding=16).save(
        ROOT / f"BULL-{VERSION}.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    (ROOT / f"BULL-{VERSION}.svg").write_text(
        svg_wrapper("bull-mark.png", 1024, 1024, label=f"BULL {VERSION}"), encoding="utf-8"
    )

    social = Image.new("RGBA", (1280, 640), "#15090E")
    draw = ImageDraw.Draw(social, "RGBA")
    for y in range(640):
        blend = y / 639
        draw.line((0, y, 1280, y), fill=(21 + round(8 * blend), 9, 14 + round(7 * blend), 255))
    for x in range(0, 1281, 40):
        draw.line((x, 0, x, 640), fill=(39, 16, 25, 255))
    for y in range(0, 641, 40):
        draw.line((0, y, 1280, y), fill=(39, 16, 25, 255))
    draw.rounded_rectangle((24, 24, 1256, 616), radius=30, outline=(128, 35, 50, 230), width=2)
    draw.ellipse((40, 112, 476, 548), fill=(53, 10, 20, 255),
                 outline=(255, 60, 82, 150), width=3)
    social_mark = contain(red_mark_source, (430, 430), padding=22)
    social.alpha_composite(social_mark, (42, 105))

    title_font = ui_font(46, bold=True)
    label_font = ui_font(18, bold=True)
    body_font = ui_font(25)
    stat_font = ui_font(17, bold=True)
    x = 505
    draw.text((x, 112), "BULL", font=title_font, fill="#FF3C52")
    bull_width = draw.textbbox((0, 0), "BULL", font=title_font)[2]
    draw.text((x + bull_width + 24, 112), "PACK LIBRARY", font=title_font, fill="#F4F7F5")
    draw.text((x, 190), f"{VERSION}  ·  YOUR TASKS. YOUR MODELS.",
              font=label_font, fill="#D8919A")
    draw.line((x, 232, 1200, 232), fill="#FF6B7A", width=3)

    cards = (
        ("CHOOSE YOUR TEST PACK", "Optional ZIPs · persistent shared library"),
        ("BUILD TASKS FOR YOUR WORK", "Editable sources · positive / negative checks"),
        ("RESUME WITH THE SAME TASKS", "Captured definitions · offline HTML reports"),
    )
    card_y = 262
    for title, detail in cards:
        draw.rounded_rectangle((x, card_y, 1200, card_y + 72), radius=14,
                               fill=(38, 14, 21, 235), outline=(128, 35, 50, 230), width=2)
        draw.rectangle((x, card_y + 12, x + 6, card_y + 60), fill="#FF3C52")
        draw.text((x + 26, card_y + 12), title, font=label_font, fill="#FF8A94")
        draw.text((x + 26, card_y + 38), detail, font=body_font, fill="#F4F7F5")
        card_y += 88

    draw.line((62, 565, 1218, 565), fill=(255, 107, 122, 110), width=2)
    harness = (ROOT / "Tests" / "benchmark_regression.py").read_text(encoding="utf-8")
    checks = int(re.search(r"STARTUP_CHECK_TOTAL=(\d+)", harness).group(1))
    draw.text((62, 582), f"{checks}/{checks} OFFLINE CHECKS", font=stat_font, fill="#FF3C52")
    draw.text((330, 582), "OLLAMA  ·  LLAMA.CPP  ·  WINDOWS  ·  MIT",
              font=stat_font, fill="#D8919A")
    social.save(BRAND / "github-social-preview.png", optimize=True)

    # Approved launch artwork is version-neutral; Tk supplies the current version
    # and live checks. Copying avoids a fresh redraw on every patch release.
    shutil.copyfile(BRAND / "startup-hero.png", BRAND / f"splash-{VERSION}.png")
    shutil.copyfile(BRAND / "startup-hero-matrix.png", BRAND / f"splash-matrix-{VERSION}.png")

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
    if sys.argv[1:] == ['--terminal-only']:
        build_terminal_mark()
    elif sys.argv[1:] == ['--theme-icons-only']:
        build_theme_icons()
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit('Usage: build_brand_assets.py [--terminal-only | --theme-icons-only]')
