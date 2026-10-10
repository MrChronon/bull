"""Explicit offline author workflow; Home and model runtime are untouched."""
from __future__ import annotations

import os
import stat
from pathlib import Path

from .i18n import get_language
from .pack_library_ui import text, label
from .evaluation.author_workshop import AuthorWorkshop
from .evaluation.pack_library import _directory, _lstat, _no_link


def show_validation(core, report):
    core.ui_print(label(report["title"]) + f" · {report['id']}@{report['version']}")
    core.ui_print(text("Tests / scored / manual: ", "Тестов / с критериями / ручных: ") +
                  f"{report['case_count']} / {report['scored_cases']} / {report['manual_cases']}")
    for row in report["checks"]:
        if row["passed"]:
            core.green()
        else:
            core.red()
        core.ui_print(("PASS " if row["passed"] else "FAIL ") + label(row["case"] + "/" + row["fixture"]) +
                      f" · {row['score']:.0%} · " + label(", ".join(row["failed_checks"]) or text("no failed checks", "нет провалов")))
        if not row["passed"]:
            core.ui_print(text("Expected: ", "Ожидалось: ") + f"{row['expected_score']:.0%} · " +
                          label(", ".join(row["expected_failed_checks"]) or text("no failed checks", "нет провалов")))
        core.white()
    core.ui_print(text("Checks cover declared rules only. Independently review reference answers and domain validity.",
                       "Проверяются только объявленные правила. Эталоны и предметную корректность проверяет человек."))


def choose_workspace(core, workshop):
    root = workshop.library.root / "Workspaces"
    core.ui_header(text("EDITABLE WORKSPACES", "РАБОЧИЕ КОПИИ"), text("Packs / Author", "Наборы / Автор"))
    directories = []
    if _directory(root):
        # Bounded listing; external prepared sources remain available by explicit path.
        for count, directory in enumerate(root.iterdir()):
            if count >= 200:
                core.ui_print(text("Showing up to 200 entries; use the exact folder path for other workspaces.",
                                   "Показано до 200 записей; для остальных копий укажите точный путь."))
                break
            details = _lstat(directory)
            if details is None:
                continue
            _no_link(directory, details)
            if stat.S_ISDIR(details.st_mode) and (directory / "author.json").is_file():
                directories.append(directory)
    directories.sort(key=lambda path: path.name)
    for index, path in enumerate(directories, 1):
        core.ui_print(f"{index}. " + label(path.name))
    raw = core.read_user_input(text("Workspace number or prepared folder path [0=back] > ",
                                    "Номер копии или путь к подготовленной папке [0=назад] > ")).strip().strip('"')
    if not raw or raw == "0":
        return None
    if raw.isdigit() and 1 <= int(raw) <= len(directories):
        return directories[int(raw) - 1]
    path = Path(os.path.abspath(raw))
    if not _directory(path):
        raise ValueError("AUTHOR_WORKSPACE_NOT_FOUND")
    return path


def workshop_menu(core):
    workshop = AuthorWorkshop(core.benchmark_pack_library())
    active = None
    while True:
        core.ui_header(text("AUTHOR WORKSHOP", "МАСТЕРСКАЯ АВТОРА"), text("Compare / Packs / Author", "Сравнение / Наборы / Автор"))
        core.ui_print(text("Edit UTF-8 source files, validate answer fixtures, then build and import a new ZIP.",
                           "Редактируйте исходники UTF-8, проверьте ответы fixtures, соберите и импортируйте новый ZIP."))
        core.ui_print(text("Workspace: ", "Рабочая копия: ") + (str(active) if active else text("none selected", "не выбрана")))
        core.ui_print(text("Installed versions and the active test selection are never edited here.",
                           "Установленные версии и активный выбор тестов здесь не меняются."))
        for key, en, ru in (
            ("1", "Create an editable starter", "Создать редактируемый пример"),
            ("2", "Choose workspace or prepared sources", "Выбрать копию или подготовленные исходники"),
            ("3", "Open selected workspace folder", "Открыть папку выбранной копии"),
            ("4", "Validate sources and answer fixtures", "Проверить исходники и примеры ответов"),
            ("5", "Build ZIP (does not install)", "Собрать ZIP (без установки)"),
            ("6", "Copy an authored installed pack to a new version", "Копировать авторский набор в новую версию"),
            ("7", "Authoring and cloud LLM instructions", "Инструкции автору и облачной LLM"),
            ("0", "Back", "Назад"),
        ):
            core.ui_menu_item(key, text(en, ru))
        raw = core.read_user_input(text("Choice > ", "Выбор > ")).strip()
        if raw in {"0", ""}:
            return
        try:
            if raw == "1":
                pack_id = core.read_user_input(text("New pack ID (lowercase letters, digits, _) [Enter=back] > ",
                                                    "ID набора (строчные латинские буквы, цифры, _) [Enter=назад] > ")).strip()
                if pack_id:
                    active = workshop.create_starter(pack_id, language=get_language())
                    core.ui_print(text("Created: ", "Создано: ") + str(active))
            elif raw == "2":
                chosen = choose_workspace(core, workshop)
                if chosen is not None:
                    active = chosen
            elif raw in {"3", "4", "5"}:
                if active is None:
                    core.ui_print(text("Create or choose a workspace first.", "Сначала создайте или выберите рабочую копию."))
                elif raw == "3":
                    if _directory(active) and hasattr(os, "startfile"):
                        os.startfile(str(active))
                    else:
                        core.ui_print(str(active))
                else:
                    report = workshop.validate(active)
                    show_validation(core, report)
                    if raw == "5" and report["passed"]:
                        destination = workshop.library.root / "PackExports" / (report["id"] + "@" + report["version"] + ".zip")
                        core.ui_print(text("ZIP includes prompts, criteria, fixture answers, README and license. Review it before sharing.",
                                           "ZIP содержит prompts, критерии, ответы fixtures, README и лицензию. Проверьте перед передачей."))
                        core.ui_print(text("Save to: ", "Сохранить в: ") + str(destination))
                        if core.read_user_input(text("Build this ZIP? [y/N] > ", "Собрать этот ZIP? [y/N] > ")).strip().casefold() in {"y", "yes", "да", "д"}:
                            target = workshop.build(active, destination, expected_source_sha256=report["source_sha256"])
                            core.green(); core.ui_print(text("ZIP ready: ", "ZIP готов: ") + str(target)); core.white()
                            core.ui_print(text("Import it through Test pack library → Import my ZIP. Nothing was published or installed.",
                                               "Импортируйте через Библиотека тестов → Импортировать свой ZIP. Ничего не опубликовано и не установлено."))
            elif raw == "6":
                identity = core.read_user_input(text("Installed pack ID@version [Enter=back] > ",
                                                     "Установленный набор ID@версия [Enter=назад] > ")).strip()
                if identity:
                    if identity.count("@") != 1:
                        raise ValueError("AUTHOR_EXACT_VERSION_REQUIRED")
                    pack_id, version = identity.split("@")
                    new_version = core.read_user_input(text("New version [Enter=back] > ", "Новая версия [Enter=назад] > ")).strip()
                    if new_version:
                        active = workshop.copy_installed(pack_id, version, new_version)
                        core.ui_print(text("Created: ", "Создано: ") + str(active))
            elif raw == "7":
                root = Path(core.__file__).resolve().parent
                for name in ("AUTHOR_WORKSHOP.md", "PACK_AUTHOR_LLM.md"):
                    core.ui_print(str(root / "Docs" / get_language() / name))
                core.ui_print(text("Edit author.json (metadata), Tasks/*.yaml or .txt, fixtures.json, README.md and LICENSE.txt.",
                                   "Редактируйте author.json (метаданные), Tasks/*.yaml или .txt, fixtures.json, README.md и LICENSE.txt."))
            core.read_user_input(text("Enter = back > ", "Enter = назад > "))
        except (ValueError, OSError, KeyError) as error:
            core.red(); core.ui_print(text("Author operation failed: ", "Ошибка мастерской: ") + label(error)); core.white()
            core.read_user_input(text("Enter = back > ", "Enter = назад > "))
