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
qualified name “BULL — Benchmarking & Usage of Local LLMs” on first mention.

`bull-mark-chafa-full-30.ansi.b64` is the UTF-8/ANSI terminal render generated
from `bull-mark-512.png` with Chafa 1.18.3 using
`chafa -f symbols -c full -s 30 bull-mark-512.png`. It is Base64-wrapped so the
release remains safe to inspect and compatible with source-control tooling;
runtime loading accepts only bounded SGR colour sequences. Chafa itself is not
required or shipped with BULL.

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

Терминальный ресурс `bull-mark-chafa-full-30.ansi.b64` получен из
`bull-mark-512.png` с помощью Chafa 1.18.3. Chafa не входит в поставку и не
требуется при запуске. Инфографика `readme-signal-panel.svg` содержит только
проверяемые сведения о проекте; нижняя схема объясняет пространство метрик и
не является результатом сравнения моделей.
