# Dependencies and rights / Зависимости и права

## English

BULL source and project documentation use the root [MIT License](LICENSE).
The package contains project source, locally compiled launchers, brand assets,
public benchmark sources and synthetic regression fixtures. It does not bundle
model weights, Ollama, llama.cpp or a Python distribution.

Python, PowerShell, Windows/.NET, Tk and separately installed model servers are
external runtime components. Setup may offer binary-wheel downloads of NumPy,
pandas, SciPy and matplotlib into a private environment; see
[the declared requirements](Setup/regression-requirements.txt). Those packages
retain their own licenses and dependency notices. Their installation requires
confirmation and is not part of the public source ZIP.

Each independently imported benchmark pack declares its own license/provenance.
An author's public/private flag does not grant rights to third-party prompts,
datasets or answers. Review those rights before sharing a pack or result.
Model weights and server engines retain their upstream licenses; using BULL
does not change them. No third-party brand endorsement is implied.

## Русский

Код и документация BULL распространяются по корневой [MIT](LICENSE).
В комплекте — исходники проекта, собранные launchers, фирменные assets,
публичные исходники наборов и синтетические fixtures. Веса моделей, Ollama,
llama.cpp и дистрибутив Python не включены.

Python, PowerShell, Windows/.NET, Tk и отдельно установленные серверы — внешние
компоненты. Setup может с подтверждением загрузить NumPy, pandas, SciPy и
matplotlib в приватное окружение; [requirements](Setup/regression-requirements.txt)
описывает этот шаг. Эти библиотеки и их зависимости сохраняют свои лицензии
и уведомления; они не входят в публичный исходный ZIP.

Импортируемые наборы объявляют собственные license/provenance. Флаг public/private
не даёт прав на чужие prompts, данные и ответы. Проверяйте права перед
публикацией наборов и результатов. Лицензии моделей/движков не меняются;
проект не заявляет одобрение со стороны владельцев сторонних марок.
