# Документация BULL v0.26.0.0

Этот файл — актуальная карта документов. Если инструкция из старого changelog или
аудита расходится с текущим руководством, приоритет имеют `USER_GUIDE.md`,
`SECURITY.md` и `AI_CONTEXT.yaml` версии v0.26.0.0.

## Начать работу

- `USER_GUIDE.md` — установка, интерфейс, Client, Benchmark Lab и диагностика.
- `UI_GUIDE.md` — короткая карта экранов и однозначные пользовательские сценарии.
- `SSH_QUICKSTART.md` — создать ключ и alias, затем подключиться одним именем.
- `BACKEND_SETUP.md` — роли Client, Server и AllInOne, Ollama и llama.cpp.
- `REMOTE_ACCESS.md` — VPN, direct SSH, белый IP и безопасная схема tunnel.

## Безопасность и публикация

- `SECURITY.md` — границы доверия, ключи, host pinning, tools и остаточные риски.
- `PUBLIC_RELEASE_CHECKLIST.md` — что проверить перед GitHub/release.
- `AUDIT_v0.26.0.0.md` — текущий аудит этапа T5.1, scorer и release boundary.
- `CODE_AUDIT.md` — текущая верхняя сводка и подробная историческая база.

## Benchmark-разработка

- `BENCHMARK_PACK_AUTHORING.md` — безопасные data-only benchmark packs.
- `../BenchmarkPacks/bull_ru_dialogue/README.md` — методика candidate pack BULL RU Dialogue.
- `AGENT_BENCHMARK.md` — Agent Benchmark MVP и его ограничения.
- `GPU_LAB.md` — экспериментальная Windows + Ollama GPU Lab.
- `PROMPTING_GUIDE.md` — prompts, версии и воспроизводимость.
- `BULL_TARGET_ARCHITECTURE.md` и `BULL_TRANSITION_ROADMAP.md` — архитектура и этапы перехода.
- `AI_CONTEXT.yaml` — машиночитаемый контекст и правила для LLM-разработчика.

## История, не текущая инструкция

Файлы `RELEASE_NOTES_0.21.0.0.md`–`RELEASE_NOTES_0.25.0.0.md`, старые changelog и
`AUDIT_v0.21.0.0.md`–`AUDIT_v0.25.0.0.md` сохранены для проверки происхождения
решений. Упомянутые в них имена файлов, namespaces, номера тестов и меню могут быть
устаревшими. Не используйте их для настройки v0.26.0.0.
