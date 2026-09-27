"""Display-only filtering; original model output is retained for scoring/storage."""
_TERMINAL_CONTROLS = {code: None for code in (*range(32), *range(127, 160)) if code not in (9, 10)}


def terminal_text(value):
    # Removing ESC/C1 at each chunk also disables split CSI/OSC sequences.
    # Newlines and tabs remain usable; carriage-return/cursor/clipboard controls do not.
    return str(value).translate(_TERMINAL_CONTROLS)
