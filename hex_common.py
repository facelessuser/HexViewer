'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
from os.path import basename

ADDRESS_OFFSET = 11
ASCII_OFFSET = 3
BITS_PER_BYTE = 8

hv_settings = sublime.load_settings('hex_viewer.sublime-settings')
hv_inspector_enable = hv_settings.get("inspector", False)


def is_enabled(current_view=None):
    window = sublime.active_window()
    if window == None:
        return False
    view = window.active_view()
    if view == None:
        return False
    # Check not only if active main view is hex,
    # check if current view is the main active view
    if current_view != None and current_view.id() != view.id():
        return False
    syntax = view.settings().get('syntax')
    language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
    return (language == "hex")


def clear_edits(view):
    view.add_regions(
        "hex_edit",
        [],
        ""
    )


def is_hex_dirty(view):
    return True if len(view.get_regions("hex_edit")) != 0 else False


def get_hex_char_range(group_size, bytes_wide):
    return int((group_size * 2) * bytes_wide / (group_size) + bytes_wide / (group_size)) - 1


def get_byte_count(start, end, group_size):
    return int((end - start - 1) / (group_size * 2 + 1)) * int(group_size) + int(((end - start - 1) % (group_size * 2 + 1)) / 2 + 1)


def ascii_to_hex_col(index, group_size):
    #   Calculate byte number              Account for address
    #
    # current_char   wanted_byte
    # ------------ = -----------  => wanted_byte + offset = start_column
    #  total_chars   total_bytes
    #
    start_column = int(ADDRESS_OFFSET + (group_size * 2) * index / (group_size) + index / (group_size))
    # Convert byte column position to test point
    return start_column


def adjust_hex_sel(view, start, end, group_size):
    bytes = 0
    size = end - start
    if view.score_selector(start, 'raw.nibble.upper') == 0:
        if view.score_selector(start, 'raw.nibble.lower'):
            start -= 1
        elif view.score_selector(start + 1, 'raw.nibble.upper') and size > 0:
            start += 1
        else:
            start = None
    # Adjust ending of selection to end of last selected byte
    if size == 0 and start != None:
        end = start + 1
        bytes = 1
    elif view.score_selector(end, 'raw.nibble.lower') == 0:
        if view.score_selector(end - 1, 'raw.nibble.lower'):
            end -= 1
        else:
            end -= 2
    if start != None and end != None:
        bytes = get_byte_count(start, end, group_size)
    return start, end, bytes


def underline(selected_bytes):
    # Convert to empty regions
    new_regions = []
    for region in selected_bytes:
        start = region.begin()
        end = region.end()
        while start < end:
            new_regions.append(sublime.Region(start))
            start += 1
    return new_regions
