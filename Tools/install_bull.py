"""The installer configures a client; it never provisions an LLM server."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'Apps'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language',choices=('en','ru'))
    parser.add_argument('--theme',choices=('bull_red','matrix_bright'))
    parser.add_argument('--desktop',default='')
    parser.add_argument('--programs',default='')
    args = parser.parse_args()
    from _bootstrap import load_compat_core
    from Shared.bull_llm.installer import InstallationServices,run_installer,text
    core = load_compat_core()
    core.console_utf8()
    core.configure_console_presentation()
    core.initialize_ui_theme()
    core.enable_console_colors()
    core.set_language(args.language or 'en')
    try:
        return run_installer(core,InstallationServices(core,desktop=args.desktop,programs=args.programs),
                             language=args.language,theme=args.theme)
    except (KeyboardInterrupt,EOFError):
        core.ui_print(text('Installer closed.','Установщик закрыт.'))
        return 2
    except Exception as error:
        core.append_client_debug('INSTALLATION_FAILED ' + type(error).__name__ + ' ' + str(error))
        core.red();core.ui_print(text('Installation failed. See client_debug.log; no server settings were installed.',
                                     'Установка не завершена. См. client_debug.log; серверные настройки не устанавливались.'));core.white()
        core.read_user_input(text('Enter = exit > ','Enter = выйти > '))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
