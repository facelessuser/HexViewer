"""
Hex Viewer.

Licensed under MIT
Copyright (c) 2011-2020 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime
from os.path import basename, splitext

ADDRESS_OFFSET = 11
ASCII_OFFSET = 3
BITS_PER_BYTE = 8
ST_SYNTAX = "sublime-syntax"


def is_enabled(current_view=None):
    """Check if hex commands should be enabled."""

    window = sublime.active_window()
    if window is None:
        return False
    view = window.active_view()
    if view is None:
        return False
    # Check not only if active main view is hex,
    # check if current view is the main active view
    if current_view is not None and current_view.id() != view.id():
        return False
    syntax = view.settings().get('syntax')
    language = splitext(basename(syntax))[0].lower() if syntax is not None else "plain text"
    return bool(language == "hexviewer")


def clear_edits(view):
    """Clear edit highlights."""
    view.add_regions(
        "hex_edit",
        [],
        ""
    )


def use_hex_lowercase():
    """Check if lowercase hex format should be used."""
    return hv_settings('use_lowercase_hex', True)


def is_hex_dirty(view):
    """Check if hex view is dirty."""

    return True if len(view.get_regions("hex_edit")) != 0 else False


def get_hex_char_range(group_size, bytes_wide):
    """Get the hex char range."""

    return int((group_size * 2) * bytes_wide / (group_size) + bytes_wide / (group_size)) - 1


def get_byte_count(start, end, group_size):
    """Get the byte count."""

    return (
        int((end - start - 1) / (group_size * 2 + 1)) * int(group_size) +
        int(((end - start - 1) % (group_size * 2 + 1)) / 2 + 1)
    )


def ascii_to_hex_col(index, group_size):
    """
    Convert ASCII selection to the column in the hex data.

          Calculate byte number              Account for address

        current_char   wanted_byte
        ------------ = -----------  => wanted_byte + offset = start_column
         total_chars   total_bytes
    """

    start_column = int(
        ADDRESS_OFFSET + (group_size * 2) * index / (group_size) +
        index / (group_size)
    )
    # Convert byte column position to test point
    return start_column


def adjust_hex_sel(view, start, end, group_size):
    """Adjust the hex selection."""

    num_bytes = 0
    size = end - start
    if view.score_selector(start, 'raw.nibble.upper') == 0:
        if view.score_selector(start, 'raw.nibble.lower'):
            start -= 1
        elif view.score_selector(start + 1, 'raw.nibble.upper') and size > 0:
            start += 1
        else:
            start = None
    # Adjust ending of selection to end of last selected byte
    if size == 0 and start is not None:
        end = start + 1
        num_bytes = 1
    elif view.score_selector(end, 'raw.nibble.lower') == 0:
        if view.score_selector(end - 1, 'raw.nibble.lower'):
            end -= 1
        else:
            end -= 2
    if start is not None and end is not None:
        num_bytes = get_byte_count(start, end, group_size)
    return start, end, num_bytes


def underline(selected_bytes):
    """Convert to empty regions to simulate underline."""

    new_regions = []
    for region in selected_bytes:
        start = region.begin()
        end = region.end()
        while start < end:
            new_regions.append(sublime.Region(start))
            start += 1
    return new_regions


def hv_settings(key=None, default=None):
    """Get the settings."""

    if key is not None:
        return sublime.load_settings('hex_viewer.sublime-settings').get(key, default)
    else:
        return sublime.load_settings('hex_viewer.sublime-settings')
