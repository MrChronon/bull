"""Read-only readiness of installed tests; never connects or installs content."""
from .evaluation.pack_selection import PackSelection


def test_library_status(core):
    status = {'count':0,'selected':None,'issues':0}
    try:
        library = core.benchmark_pack_library()
        rows = library.scan()
        status['count'] = sum(row.pack is not None and row.pack.runnable for row in rows)
        status['issues'] = sum(row.pack is None for row in rows)
        try:
            status['selected'] = PackSelection(library).snapshot()
        except (ValueError, OSError, KeyError, TypeError):
            status['issues'] += 1
    except (ValueError, OSError, KeyError, TypeError):
        status['issues'] += 1
    return status
