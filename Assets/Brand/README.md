# BULL brand assets

The approved bull silhouette represents decisive performance testing. Neural
nodes inside the head represent LLM inference; the red horn bars represent
measured benchmark results in the public v0.27 presentation.

- Base primary: `#00E6A8`
- Base secondary: `#24D6FF`
- Graphite: `#111820`
- Off-white: `#F4F7F5`

The source master stays unchanged. The public GitHub presentation uses the
generated `bull-wordmark-red.png`, `bull-mark-red.png` and red social preview:

- Release red: `#FF3C52`
- Release red soft: `#FF8A94`

`bull-logo-canonical.png` is the immutable source. Its SHA-256, dimensions and
approved crop boxes are recorded in `brand-lock.json`. Run
`Tools/build_brand_assets.py` to reproduce release variants; it refuses a changed
master. Do not redraw, stretch, rotate or recolour the canonical artwork.

Use `bull-mark-on-light.png` or `bull-mark-on-dark.png` when a fixed background is
needed and `bull-mark-mono.png` where only one colour is available. Use the
qualified name “BULL — Benchmarking & Usage of Local Language Models” on first mention.

`bull-mark-console-48.ansi.b64` is the 48-column, 24-row terminal render from the
locked master crop. Reproduce it with
`python Tools/build_brand_assets.py --terminal-only`. Coloured background cells
and ordinary ASCII spaces preserve the bull without relying on a font's block
glyphs. Each row resets its colours. Runtime loading accepts only fixed-size RGB
background cells; a plain ASCII silhouette is used when colours are unavailable.
Pillow is a build-time dependency only; no image renderer is required at runtime.
One direct resample preserves more detail than the previous 30×15 resource.
`bull-icon-matrix.ico` is the green BULL Matrix shortcut icon. `bull-setup.ico`
adds a small install-arrow badge to the red bull for `Setup.exe`.
Reproduce these icons with `python Tools/build_brand_assets.py --theme-icons-only`.
Approved red/green startup artwork is unchanged.

`readme-signal-panel.svg` is a repository presentation infographic. Its figures
are verified project facts, while the lower section is a conceptual measurement
map rather than benchmark data or model scores. Update the displayed counts only
after the corresponding regression, benchmark-pack and artifact contracts have
been verified.

## Русский

Утверждённый силуэт быка обозначает измерение производительности, внутренние
узлы — LLM inference, а красные элементы рогов — результаты бенчмарков в
публичном оформлении v0.27.
Неизменяемый исходник — `bull-logo-canonical.png`; его контрольная сумма,
размеры и допустимые области кадрирования записаны в `brand-lock.json`.
Варианты для релиза воспроизводятся командой `Tools/build_brand_assets.py`.
Красные файлы `bull-wordmark-red.png`, `bull-mark-red.png` и social preview —
производные от неизменяемого исходника, а не замена master-файла.

Терминальный ресурс `bull-mark-console-48.ansi.b64` получен из утверждённого
кадрирования исходника командой `python Tools/build_brand_assets.py --terminal-only`.
Размер — 48 столбцов и 24 строки, с одним масштабированием из исходника. Цветные фоновые ячейки с обычными пробелами
не требуют редких символов шрифта; каждая строка сбрасывает цвет. Загрузчик
принимает только RGB-ячейки фиксированного размера. Без поддержки цвета выводится
ASCII-силуэт. Pillow нужен только для сборки, но не при запуске приложения.
Инфографика `readme-signal-panel.svg` содержит только
проверяемые сведения о проекте; нижняя схема объясняет пространство метрик и
не является результатом сравнения моделей.
# Versioned startup splashes

`splash-v*.png` is the release artwork for the integrity-check screen shown
before BULL opens its main menu. The terminal application never invokes Chafa
or an image viewer for this screen.

`splash-vX.Y.Z.png` is the versioned native desktop startup image. BULL opens
it in a small stdlib-Tk window only while the mandatory offline verification
runs; it is never rendered into the terminal.

The client uses the asset matching `APP_VERSION`, verifies that the requested
asset is an exact local versioned file, and never accepts a user-provided image
path for this screen.
