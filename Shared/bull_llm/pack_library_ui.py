"""Pack Library pages. Downloads are explicit; archives never supply program code."""
from __future__ import annotations

import os
from pathlib import Path

from .i18n import get_language
from .presentation import terminal_text
from .evaluation.pack_selection import PackSelection
from .evaluation.catalog import EXECUTABLE_SCORER_REFS


def text(en, ru):
    return ru if get_language() == "ru" else en


def label(value, limit=180):
    return " ".join(terminal_text(str(value)).split())[:limit]


def describe(core, pack):
    core.ui_print(label(pack.title) + " · " + pack.identity)
    core.ui_print(text("Status / visibility: ", "Статус / видимость: ") +
                  pack.status.value + " / " + pack.visibility.value)
    core.ui_print(text("Source / author: ", "Источник / автор: ") +
                  label(pack.manifest.get("provenance", {})))
    core.ui_print(text("License: ", "Лицензия: ") + label(pack.manifest["license"]["name"]))
    core.ui_print(text("Skills: ", "Области: ") + label(", ".join(pack.manifest["taxonomy"])))
    languages = sorted({str(case.definition.get("expected_language") or
                            case.definition.get("language_track") or
                            (case.definition.get("constraints") or {}).get("language") or "unspecified")
                        for case in pack.cases})
    core.ui_print(text("Declared languages: ", "Заявленные языки: ") + label(", ".join(languages)))
    core.ui_print(text("Tests: ", "Тестов: ") + str(len(pack.cases)))
    core.ui_print(label(pack.manifest.get("description", ""), 500))
    core.ui_print(text("Unscored tests require manual review; no automatic quality score is invented.",
                       "Тесты без скорера требуют ручной оценки; автоматический балл не выдумывается."))
    core.ui_print(text("Engine-owned code checks execute model output; this is not a sandbox. Use a disposable VM.",
                       "Проверки кода движка запускают код ответа модели; это не песочница. Используйте одноразовую VM."))


def case_page(core, pack, page, *, selecting=True):
    start = page * 12
    for index, case in enumerate(pack.cases[start:start + 12], start + 1):
        item = case.definition
        core.ui_print(f"{index:>3}. {case.id} · {label(case.category)} · {case.scorer_ref}")
        core.ui_print("     " + label(item.get("description", "")))
        constraints = item.get("constraints") or {}
        core.ui_print("     " + text("Limits / author settings: ", "Ограничения / параметры автора: ") + label({
            key: item[key] for key in ("primary_predict", "recovery_predict", "benchmark_ctx", "think_override", "benchmark_defaults")
            if key in item
        }) + " · " + label(constraints))
    if selecting:
        core.ui_print(text("n/p = next/previous page; all = entire pack; numbers separated by commas = subset.",
                           "n/p = следующая/предыдущая страница; all = весь набор; номера через запятую = часть."))


def library_status(core):
    from .readiness import test_library_status
    status = test_library_status(core)
    selected = status['selected']
    detail = str(status['count']) + text(' installed', ' установлено')
    if selected:
        detail += ' · ' + selected['identity'] + f" · {selected['selected_cases']}/{selected['total_cases']}"
    else:
        detail += text(' · none selected', ' · ничего не выбрано')
    if status['issues']:
        detail += text(' · validation required', ' · требуется проверка')
    core.ui_status_strip([(text('Test packs', 'Наборы'), detail,
        'ok' if selected and status['count'] and not status['issues'] else 'warn')])


def installed_pack_browser(core):
    """Read-only pack -> case browser. Never changes the active selection."""
    library = core.benchmark_pack_library()
    while True:
        core.ui_header(text('INSTALLED PACKS', 'УСТАНОВЛЕННЫЕ НАБОРЫ'),
                       text('Test settings / Browse', 'Настройки тестов / Просмотр'))
        core.ui_print(text('Folder: ', 'Папка: ') + str(library.root))
        findings = library.scan()
        for index, finding in enumerate(findings, 1):
            pack = finding.pack
            core.ui_menu_item(str(index), label(pack.title) if pack else label(finding.path.name),
                pack.identity + f' · {len(pack.cases)} ' + text('tests', 'тестов') if pack else
                text('Unavailable: ', 'Недоступен: ') + label(finding.error_code))
        if not findings:
            core.ui_print(text('No packs installed.', 'Наборы не установлены.'))
        core.ui_menu_item('0', text('Back', 'Назад'))
        value = core.read_user_input(text('Pack [0=back] > ', 'Набор [0=назад] > ')).strip()
        if value in ('', '0'): return
        if not value.isdigit() or not 1 <= int(value) <= len(findings): continue
        pack = findings[int(value)-1].pack
        if pack is None: continue
        page = 0
        while True:
            core.ui_header(text('PACK TESTS', 'ТЕСТЫ НАБОРА'), label(pack.identity))
            describe(core, pack)
            case_page(core, pack, page, selecting=False)
            core.ui_print(text('Read-only view; selection is unchanged.', 'Только просмотр; выбор для прогона не меняется.'))
            raw = core.read_user_input(text('n/p=next/previous; 0=back > ',
                                            'n/p=следующая/предыдущая; 0=назад > ')).strip().casefold()
            if raw in ('', '0'): break
            if raw in ('n','p'):
                page = min(max(0, page + (1 if raw == 'n' else -1)), (len(pack.cases)-1)//12)


def choose_language_pack(core, suite):
    """Select one installed compatible version before any model discovery."""
    store = PackSelection(core.benchmark_pack_library())
    required = list(core.LANGUAGE_SUITE_DEFINITIONS[suite]['tests'])
    while True:
        core.ui_header(text('LANGUAGE TEST PACK', 'НАБОР ЯЗЫКОВЫХ ТЕСТОВ'), suite)
        packs = [row.pack for row in store.library.scan() if row.pack is not None and row.pack.runnable
                 and set(required).issubset({case.id for case in row.pack.cases})]
        for index, pack in enumerate(packs, 1):
            core.ui_menu_item(str(index), label(pack.title), pack.identity + f' · {len(required)} ' + text('tests', 'тестов'))
        if not packs:
            core.yellow(); core.ui_print(text('Install the language comparison ZIP in Test settings first.',
                'Сначала установите ZIP языкового набора в настройках тестов.')); core.white()
        core.ui_menu_item('T', text('Install or manage packs', 'Установка и управление наборами'))
        core.ui_menu_item('0', text('Back', 'Назад'))
        choice = core.read_user_input(text('Pack [0=back, T=settings] > ', 'Набор [0=назад, T=настройки] > ')).strip().casefold()
        if choice in ('', '0'): return False
        if choice == 't':
            library_menu(core)
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(packs):
            pack = packs[int(choice)-1]
            store.select(pack.id, pack.version, required)
            return True


def choose_cases(core, store, pack):
    page = 0
    while True:
        core.ui_header(text("CHOOSE TESTS", "ВЫБОР ТЕСТОВ"), text("Compare / Pack", "Сравнение / Набор"))
        describe(core, pack)
        case_page(core, pack, page)
        raw = core.read_user_input(text("Tests [all, 0=back] > ", "Тесты [all, 0=назад] > ")).strip().casefold() or "all"
        if raw == "0":
            return False
        if raw in {"n", "p"}:
            page = min(max(0, page + (1 if raw == "n" else -1)), (len(pack.cases) - 1) // 12)
            continue
        try:
            if raw == "all":
                ids = None
            else:
                numbers = [int(x.strip()) for x in raw.split(",")]
                if not numbers or len(numbers) != len(set(numbers)) or any(x < 1 or x > len(pack.cases) for x in numbers):
                    raise ValueError("TEST_SELECTION_INVALID")
                ids = [pack.cases[x - 1].id for x in numbers]
            selected = {case.id for case in pack.cases} if ids is None else set(ids)
            code_cases = [case.id for case in pack.cases if case.id in selected and case.scorer_ref in EXECUTABLE_SCORER_REFS]
            approved = False
            if code_cases:
                core.ui_print(text("Code execution required: ", "Нужно выполнение кода: ") + ", ".join(code_cases))
                approved = core.read_user_input(text(
                    "Allow model code execution on this computer? Type EXECUTE, or Enter to cancel > ",
                    "Разрешить код модели на этом компьютере? Введите EXECUTE или Enter для отмены > ")).strip() == "EXECUTE"
                if not approved:
                    return False
            store.select(pack.id, pack.version, ids, allow_code_execution=approved)
            return True
        except ValueError:
            core.ui_print(text("Invalid selection. Use distinct test numbers from this pack.",
                               "Некорректный выбор. Укажите неповторяющиеся номера тестов этого набора."))
            core.read_user_input(text("Enter = retry > ", "Enter = повторить > "))


def install(core, store, archive):
    preview = store.library.inspect_zip(archive)
    core.ui_header(text("INSTALL PREVIEW", "ПРОСМОТР ПЕРЕД УСТАНОВКОЙ"), "Pack Library / ZIP")
    describe(core, preview)
    core.ui_print(text("Destination: ", "Папка установки: ") + str(store.library.root))
    core.ui_print(text("Existing versions are preserved. No program code is loaded from the ZIP.",
                       "Существующие версии сохраняются. Программный код из ZIP не загружается."))
    if core.read_user_input(text("Install this version? [y/N] > ", "Установить эту версию? [y/N] > ")).strip().casefold() not in {"y", "yes", "д", "да"}:
        return False
    pack = store.library.install_zip(archive, expected_compiled_sha256=preview.compiled_sha256,
                                    expected_manifest_sha256=preview.manifest_sha256)
    return choose_cases(core, store, pack)


def base_archive_menu(core, store):
    directory = Path(core.__file__).resolve().parent / "BasePacks"
    archives = sorted(directory.glob("*.zip"))
    core.ui_header(text("BASE PACKS", "БАЗОВЫЕ НАБОРЫ"), "Pack Library / BasePacks")
    for index, archive in enumerate(archives, 1):
        core.ui_print(f"{index}. {archive.name}")
    if not archives:
        core.ui_print(text("No bundled ZIP found. Import a downloaded pack ZIP instead.",
                           "В поставке не найден ZIP. Импортируйте скачанный ZIP набора."))
    raw = core.read_user_input(text("Packs [comma-separated numbers, all, 0=back] > ",
                                    "Наборы [номера через запятую, all, 0=назад] > ")).strip()
    if raw in {'', '0'}:
        return False
    numbers = parse_pack_numbers(raw, len(archives))
    if len(numbers) == 1:
        return install(core, store, archives[numbers[0]])
    install_archives(core, store, [archives[index] for index in numbers])
    return False


def install_archives(core, store, archives, *, select_default=False):
    previews = [(archive, store.library.inspect_zip(archive)) for archive in archives]
    if not previews:raise ValueError('PACK_ARCHIVES_NOT_FOUND')
    core.ui_header(text("INSTALL PACKS", "УСТАНОВКА НАБОРОВ"), "Pack Library / ZIP")
    for archive, preview in previews:
        describe(core, preview)
    core.ui_print(text("Destination: ", "Папка установки: ") + str(store.library.root))
    core.ui_print(text("Installation does not activate packs. A run uses one selected pack only.",
                       "Установка не включает наборы в прогон. Для запуска выберите один набор и его тесты."))
    if core.read_user_input(text("Install these packs? [y/N] > ", "Установить эти наборы? [y/N] > ")).strip().casefold() not in {'y', 'yes', 'д', 'да'}:
        return False
    findings = {row.pack.identity: row.pack for row in store.library.scan() if row.pack is not None}
    successful = 0
    for archive, preview in previews:
        try:
            existing = findings.get(preview.identity)
            if existing is not None:
                if (existing.compiled_sha256, existing.manifest_sha256) != (preview.compiled_sha256, preview.manifest_sha256):
                    raise ValueError('PACK_VERSION_EXISTS: different content; use a new version')
                core.ui_print(text("Already installed: ", "Уже установлен: ") + preview.identity)
            else:
                store.library.install_zip(archive, expected_compiled_sha256=preview.compiled_sha256,
                                          expected_manifest_sha256=preview.manifest_sha256)
                core.green(); core.ui_print(text("Installed: ", "Установлен: ") + preview.identity); core.white()
            successful += 1
        except (ValueError, OSError) as error:
            core.yellow(); core.ui_print(preview.identity + ' · ' + label(error)); core.white()
    if successful:
        store.finish_onboarding()
        if select_default and successful == len(previews):
            # Only the safe chat pack is selected automatically, never code tests.
            default = next((pack for _, pack in previews if pack.id == 'bull_chat_core'), None)
            if default is not None:store.select(default.id, default.version)
    core.ui_print(text("Available: ", "Доступно: ") + f'{successful}/{len(previews)}')
    return successful == len(previews)


def parse_pack_numbers(raw, count):
    value = str(raw).strip().casefold()
    if value == 'all' and count > 0:
        return list(range(count))
    try:
        numbers = [int(part.strip()) for part in value.split(',')]
    except ValueError:
        raise ValueError('PACK_SELECTION_INVALID') from None
    if not numbers or len(numbers) != len(set(numbers)) or any(x < 1 or x > count for x in numbers):
        raise ValueError('PACK_SELECTION_INVALID')
    return [number - 1 for number in numbers]


def select_for_run(core, store):
    """Direct pack picker; library management is optional, not an extra mandatory page."""
    while True:
        core.ui_header(text('SELECT TEST PACK','ВЫБОР НАБОРА ТЕСТОВ'),
                       text('Model testing / Pack','Тестирование моделей / Набор'))
        try:active = store.snapshot()
        except (ValueError,OSError,KeyError):active = None
        findings = [row.pack for row in store.library.scan() if row.pack is not None and row.pack.runnable]
        if active:
            core.ui_print(text('Current selection: ','Текущий выбор: ') + active['identity'] +
                          f" · {active['selected_cases']}/{active['total_cases']}")
        for index, pack in enumerate(findings,1):
            core.ui_menu_item(str(index),label(pack.title),pack.identity + f' · {len(pack.cases)} ' + text('tests','тестов'))
        if not findings:
            core.yellow();core.ui_print(text('No usable packs. Install them in Test settings.',
                                             'Нет доступных наборов. Установите их в настройках тестов.'));core.white()
        core.ui_menu_item('T',text('Install or manage packs','Установка и управление наборами'))
        core.ui_menu_item('0',text('Back','Назад'))
        raw = core.read_user_input(text('Pack [Enter=current, T=settings, 0=back] > ',
                                        'Набор [Enter=текущий, T=настройки, 0=назад] > ')).strip().casefold()
        if raw == '0':return False
        if not raw and active:return True
        if raw == 't':
            if library_menu(core):return True
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(findings):
            if choose_cases(core,store,findings[int(raw)-1]):return True


def library_menu(core, *, onboarding=False, choose=False):
    store = PackSelection(core.benchmark_pack_library())
    if choose and not onboarding:return select_for_run(core,store)
    if onboarding and store.read()["onboarding_complete"]:
        return False
    while True:
        core.ui_header(text("TEST PACK LIBRARY", "БИБЛИОТЕКА ТЕСТОВ"), text("Compare / Packs", "Сравнение / Наборы"))
        if not onboarding:library_status(core)
        core.ui_print(text("Base test packs are supplied with the application. Install them, import your own pack, or skip installation for now.",
                           "В комплекте с программой поставляются базовые наборы тестов. Установите их, импортируйте свой набор или пока пропустите установку."))
        core.ui_print(text("Each run uses one selected pack version: all its tests or a subset.",
                           "Для одного запуска выбирается одна версия одного набора: все его тесты или часть."))
        core.ui_print(text("Persistent folder: ", "Общая пользовательская папка: ") + str(store.library.root))
        core.ui_print(text("Packs survive application updates. Download ZIPs from their authors; there is no automatic network catalog.",
                           "Наборы сохраняются при обновлении приложения. ZIP можно скачать у автора; сетевого каталога пока нет."))
        try:
            active = store.snapshot()
            core.ui_print(text("Selected: ", "Выбрано: ") + (active["identity"] +
                          f" · {active['selected_cases']}/{active['total_cases']}" if active else text("none", "ничего")))
        except (ValueError, OSError, KeyError) as error:
            core.ui_print(text("Selection unavailable: ", "Выбор недоступен: ") + label(error))
        core.ui_menu_item("1", text("Install a base pack", "Установить базовый набор"), "BasePacks/*.zip")
        core.ui_menu_item("2", text("Import ZIP: file or HTTPS link", "Импортировать ZIP: файл или HTTPS-ссылка"))
        core.ui_menu_item("3", text("Choose installed pack and tests", "Выбрать установленный набор и тесты"))
        if not onboarding:
            core.ui_menu_item("4", text("Remove one installed version", "Удалить одну установленную версию"),
                              text("Moved to BULL's internal bin; recoverable", "Перенос в корзину BULL; можно восстановить"))
            core.ui_menu_item("5", text("Open library folder", "Открыть папку библиотеки"))
            core.ui_menu_item("6", text("Author Workshop", "Мастерская автора"),
                              text("Editable tasks, fixture checks and ZIP builder", "Редактируемые задания, проверка критериев и сборка ZIP"))
            core.ui_menu_item("7", text("Browse installed packs and tests", "Просмотреть установленные наборы и тесты"))
        core.ui_menu_item("0", text("Skip for now" if onboarding else "Back", "Пока пропустить" if onboarding else "Назад"))
        raw = core.read_user_input(text("Choice > ", "Выбор > ")).strip()
        if raw in {"0", ""}:
            if onboarding:
                store.finish_onboarding()
            return False
        try:
            if raw == "1":
                if base_archive_menu(core, store):
                    return True
            elif raw == "2":
                source = core.read_user_input(text("ZIP path or HTTPS link [Enter=back] > ", "Путь к ZIP или HTTPS-ссылка [Enter=назад] > ")).strip().strip('"')
                if source:
                    from .pack_download import archive_source
                    with archive_source(source) as archive:
                        if install(core, store, archive):return True
            elif raw == "3" or (raw == "4" and not onboarding):
                findings = store.library.scan()
                core.ui_header(text("INSTALLED PACKS", "УСТАНОВЛЕННЫЕ НАБОРЫ"), "Pack Library / Installed")
                for index, row in enumerate(findings, 1):
                    if row.pack:
                        size = store.library.size_bytes(row.pack.id, row.pack.version)
                        core.ui_print(f"{index}. {row.pack.identity} · {label(row.pack.title)} · {row.pack.status.value} · {size / 1024:.1f} KiB")
                    else:
                        core.ui_print(f"{index}. {label(row.path.name)} · INVALID · {label(row.error_code)}")
                choice_raw = core.read_user_input(text("Version [0=back] > ", "Версия [0=назад] > ")).strip()
                if not choice_raw.isdigit() or not 1 <= int(choice_raw) <= len(findings):
                    continue
                pack = findings[int(choice_raw) - 1].pack
                if pack is None:
                    core.ui_print(text("Invalid pack cannot be selected. Inspect or remove its directory manually.",
                                       "Повреждённый набор выбрать нельзя. Проверьте или уберите его папку вручную."))
                elif raw == "3":
                    if choose_cases(core, store, pack):
                        return True
                elif core.read_user_input(text("Move this version to BULL's bin? [y/N] > ", "Перенести эту версию в корзину BULL? [y/N] > ")).strip().casefold() in {"y", "yes", "да", "д"}:
                    target = store.library.move_to_trash(pack.id, pack.version)
                    selected = store.read()["selection"]
                    if selected and (selected["id"], selected["version"]) == (pack.id, pack.version):
                        store.clear()
                    core.ui_print(text("Moved to: ", "Перенесено в: ") + str(target))
            elif raw == "5" and not onboarding:
                if store.library.root.is_dir() and hasattr(os, "startfile"):
                    os.startfile(str(store.library.root))
                else:
                    core.ui_print(text("Folder does not exist yet: ", "Папка пока не создана: ") + str(store.library.root))
            elif raw == "6" and not onboarding:
                from .author_workshop_ui import workshop_menu
                workshop_menu(core)
                continue
            elif raw == "7" and not onboarding:
                installed_pack_browser(core)
                continue
            core.read_user_input(text("Enter = back > ", "Enter = назад > "))
        except (ValueError, OSError, KeyError, ImportError) as error:
            if hasattr(core, 'append_client_debug'):
                core.append_client_debug('PACK_LIBRARY_ACTION_FAILED', error, include_traceback=True)
            core.ui_print(text("Pack operation failed: ", "Не удалось выполнить действие: ") + label(error))
            core.read_user_input(text("Enter = back > ", "Enter = назад > "))


def selection_preview(core, snapshot):
    core.ui_print(text("Pack: ", "Набор: ") + label(snapshot["identity"]) + " · " + label(snapshot["title"]))
    core.ui_print(text("Selection: ", "Выбор: ") + f"{snapshot['selected_cases']}/{snapshot['total_cases']} · " + snapshot["reason"])
    if snapshot["coverage"] == "subset":
        core.yellow()
        core.ui_print(text("SUBSET: this is not a full-pack benchmark result.", "ЧАСТЬ НАБОРА: результат не является оценкой полного набора."))
        core.white()
