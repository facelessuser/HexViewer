'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
import math
from struct import unpack
from hex_common import *

hv_endianness = hv_settings.get("inspector_endian", "little")


class HexShowInspectorCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and hv_inspector_enable

    def run(self):
        # Setup inspector window
        view = self.window.get_output_panel('hex_viewer_inspector')
        view.set_syntax_file("Packages/HexViewer/HexInspect.hidden-tmLanguage")
        view.settings().set("draw_white_space", "none")
        view.settings().set("draw_indent_guides", False)
        view.settings().set("gutter", "none")
        view.settings().set("line_numbers", False)
        # Show
        self.window.run_command("show_panel", {"panel": "output.hex_viewer_inspector"})
        self.window.run_command("hex_inspector", {"reset": True})


class HexHideInspectorCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and hv_inspector_enable

    def run(self):
        self.window.run_command("hide_panel", {"panel": "output.hex_viewer_inspector"})


class HexToggleInspectorEndiannessCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and hv_inspector_enable

    def run(self):
        global hv_endianness
        hv_endianness = "big" if hv_endianness == "little" else "little"
        self.window.run_command('hex_highlighter')


class HexInspectorCommand(sublime_plugin.WindowCommand):
    def get_bytes(self, start, bytes_wide):
        bytes = self.view.substr(sublime.Region(start, start + 2))
        byte64 = None
        byte32 = None
        byte16 = None
        byte8 = None
        start += 2
        size = self.view.size()
        count = 1
        group_divide = 1
        address = 12
        ascii_divide = group_divide + bytes_wide + address + 1
        target_bytes = 8

        # Look for 64 bit worth of bytes
        while start < size and count < target_bytes:
            # Check if sitting on first nibble
            if self.view.score_selector(start, 'raw.nibble.upper'):
                bytes += self.view.substr(sublime.Region(start, start + 2))
                count += 1
                start += 2
            else:
                # Must be at byte group falling edge; try and step over divider
                start += group_divide
                if start < size and self.view.score_selector(start, 'raw.nibble.upper'):
                    bytes += self.view.substr(sublime.Region(start, start + 2))
                    count += 1
                    start += 2
                # Must be at line end; try and step to next line
                else:
                    start += ascii_divide
                    if start < size and self.view.score_selector(start, 'raw.nibble.upper'):
                        bytes += self.view.substr(sublime.Region(start, start + 2))
                        count += 1
                        start += 2
                    else:
                        # No more bytes to check
                        break

        byte8 = bytes[0:2]
        if count > 1:
            byte16 = bytes[0:4]
        if count > 3:
            byte32 = bytes[0:8]
        if count > 7:
            byte64 = bytes[0:16]
        return byte8, byte16, byte32, byte64

    def display(self, view, byte8, bytes16, bytes32, bytes64):
        item_dec = "%-12s:  %-14d"
        item_str = "%-12s:  %-14s"
        item_float = "%-12s:  %-14e"
        item_double = "%-12s:  %-14e"
        nl = "\n"
        endian = ">" if self.endian == "big" else "<"
        i_buffer = "%28s:%-28s" % ("Hex Inspector ", (" Big Endian" if self.endian == "big" else " Little Endian")) + nl
        if byte8 != None:
            i_buffer += item_dec * 2 % (
                "byte", unpack(endian + "B", byte8.decode("hex"))[0],
                "short", unpack(endian + "b", byte8.decode("hex"))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "byte", "--",
                "short", "--"
            ) + nl
        if bytes16 != None:
            i_buffer += item_dec * 2 % (
                "word", unpack(endian + "H", bytes16.decode("hex"))[0],
                "int", unpack(endian + "h", bytes16.decode("hex"))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "word", "--",
                "int", "--"
            ) + nl
        if bytes32 != None:
            i_buffer += item_dec * 2 % (
                "dword", unpack(endian + "I", bytes32.decode("hex"))[0],
                "longint", unpack(endian + "i", bytes32.decode("hex"))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "dword", "--",
                "longint", "--"
            ) + nl
        if bytes32 != None:
            s_float = unpack(endian + "f", bytes32.decode('hex'))[0]
            if math.isnan(s_float):
                i_buffer += item_str % ("float", "NaN")
            else:
                i_buffer += item_float % (
                    "float", s_float
                )
        else:
            i_buffer += item_str % ("float", "--")
        if bytes64 != None:
            d_float = unpack(endian + "d", bytes64.decode('hex'))[0]
            if math.isnan(d_float):
                i_buffer += item_str % ("double", "NaN") + nl
            else:
                i_buffer += item_double % (
                    "double", d_float
                ) + nl
        else:
            i_buffer += item_str % ("double", "--") + nl
        if byte8 != None:
            i_buffer += item_str % ("binary", '{0:08b}'.format(unpack(endian + "B", byte8.decode("hex"))[0])) + nl
        else:
            i_buffer += item_str % ("binary", "--") + nl

        # Update content
        view.set_read_only(False)
        edit = view.begin_edit()
        view.replace(edit, sublime.Region(0, view.size()), i_buffer)
        view.end_edit(edit)
        view.set_read_only(True)
        view.sel().clear()

    def is_enabled(self):
        return is_enabled()

    def run(self, first_byte=None, bytes_wide=None, reset=False):
        self.view = self.window.active_view()
        self.endian = hv_endianness
        byte8, bytes16, bytes32, bytes64 = None, None, None, None
        if not reset and first_byte != None and bytes_wide != None:
            byte8, bytes16, bytes32, bytes64 = self.get_bytes(int(first_byte), int(bytes_wide))
        self.display(self.window.get_output_panel('hex_viewer_inspector'), byte8, bytes16, bytes32, bytes64)
