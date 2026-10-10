"""Per-console font bootstrap; never changes Terminal profiles or registry."""
import ctypes
import os
import sys


class Coord(ctypes.Structure):
    _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]


class ConsoleFont(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint32), ('nFont', ctypes.c_uint32),
                ('dwFontSize', Coord), ('FontFamily', ctypes.c_uint32),
                ('FontWeight', ctypes.c_uint32), ('FaceName', ctypes.c_wchar * 32)]


def configure_font():
    if os.name != 'nt' or os.environ.get('WT_SESSION') or not sys.stdout.isatty():
        return False
    try:
        kernel = ctypes.windll.kernel32
        kernel.GetStdHandle.restype = ctypes.c_void_p
        kernel.GetCurrentConsoleFontEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ConsoleFont)]
        kernel.SetCurrentConsoleFontEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ConsoleFont)]
        handle = kernel.GetStdHandle(-11)
        font = ConsoleFont(); font.cbSize = ctypes.sizeof(font)
        if not kernel.GetCurrentConsoleFontEx(handle, False, ctypes.byref(font)):
            return False
        font.dwFontSize = Coord(0, 20)
        font.FontFamily = 54
        font.FontWeight = 400
        font.FaceName = 'Consolas'
        return bool(kernel.SetCurrentConsoleFontEx(handle, False, ctypes.byref(font)))
    except (AttributeError, OSError, ValueError):
        return False
