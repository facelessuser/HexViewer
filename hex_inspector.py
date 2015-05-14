"""
Hex Viewer.

Licensed under MIT
Copyright (c) 2011-2015 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime
import sublime_plugin
import math
from struct import unpack
import HexViewer.hex_common as common
from binascii import unhexlify

hv_endianness = None


class HexShowInspectorCommand(sublime_plugin.WindowCommand):

    """Show the hex inspector panel."""

    def is_enabled(self):
        """Check if command is enabled."""

        return bool(common.is_enabled() and common.hv_settings("inspector", False))

    def run(self):
        """Run the command."""

        # Setup inspector window
        view = self.window.get_output_panel('hex_viewer_inspector')
        view.set_syntax_file("Packages/HexViewer/HexInspect.%s" % common.ST_SYNTAX)
        view.settings().set("draw_white_space", "none")
        view.settings().set("draw_indent_guides", False)
        view.settings().set("gutter", False)
        view.settings().set("line_numbers", False)
        # Show
        self.window.run_command("show_panel", {"panel": "output.hex_viewer_inspector"})
        self.window.run_command("hex_inspector", {"reset": True})


class HexHideInspectorCommand(sublime_plugin.WindowCommand):

    """Hide the hex inspector panel."""

    def is_enabled(self):
        """Check if command is enabled."""

        return bool(common.is_enabled() and common.hv_settings("inspector", False))

    def run(self):
        """Run the command."""

        self.window.run_command("hide_panel", {"panel": "output.hex_viewer_inspector"})


class HexToggleInspectorEndiannessCommand(sublime_plugin.WindowCommand):

    """Toggle hex inspector's endianness."""

    def is_enabled(self):
        """Check if command is enabled."""

        return bool(common.is_enabled() and common.hv_settings("inspector", False))

    def run(self):
        """Run the command."""

        global hv_endianness
        hv_endianness = "big" if hv_endianness == "little" else "little"
        self.window.run_command('hex_highlighter')


class HexInspectGlobal(object):

    """Global hex inspector data."""

    bfr = None
    region = None

    @classmethod
    def clear(cls):
        """Clear."""

        cls.bfr = None
        cls.region = None


class HexInspectorApplyCommand(sublime_plugin.TextCommand):

    """Apply text to the hex inspector panel."""

    def run(self, edit):
        """Run the command."""

        self.view.replace(edit, HexInspectGlobal.region, HexInspectGlobal.bfr)


class HexInspectorCommand(sublime_plugin.WindowCommand):

    """Hex inspector command."""

    def get_bytes(self, start, bytes_wide):
        """Get the bytes at the cursor."""

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
        """Display hex inspector data."""

        item_dec = common.hv_settings("inspector_integer_format", "%-12s:  %-14d")
        item_str = common.hv_settings("inspector_missing/bad_format", "%-12s:  %-14s")
        item_float = common.hv_settings("insepctor_float_format", "%-12s:  %-14e")
        item_double = common.hv_settings("inspector_double_format", "%-12s:  %-14e")
        item_bin = common.hv_settings("inspector_binary_format", "%-12s:  %-14s")
        nl = "\n"
        endian = ">" if self.endian == "big" else "<"
        i_buffer = "%28s:%-28s" % ("Hex Inspector ", (" Big Endian" if self.endian == "big" else " Little Endian")) + nl
        if byte8 is not None:
            i_buffer += item_dec * 2 % (
                "byte", unpack(endian + "B", unhexlify(byte8))[0],
                "short", unpack(endian + "b", unhexlify(byte8))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "byte", "--",
                "short", "--"
            ) + nl
        if bytes16 is not None:
            i_buffer += item_dec * 2 % (
                "word", unpack(endian + "H", unhexlify(bytes16))[0],
                "int", unpack(endian + "h", unhexlify(bytes16))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "word", "--",
                "int", "--"
            ) + nl
        if bytes32 is not None:
            i_buffer += item_dec * 2 % (
                "dword", unpack(endian + "I", unhexlify(bytes32))[0],
                "longint", unpack(endian + "i", unhexlify(bytes32))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "dword", "--",
                "longint", "--"
            ) + nl
        if bytes64 is not None:
            i_buffer += item_dec * 2 % (
                "qword", unpack(endian + "Q", unhexlify(bytes64))[0],
                "longlongint", unpack(endian + "q", unhexlify(bytes64))[0]
            ) + nl
        else:
            i_buffer += item_str * 2 % (
                "qword", "--",
                "longlongint", "--"
            ) + nl
        if bytes32 is not None:
            s_float = unpack(endian + "f", unhexlify(bytes32))[0]
            if math.isnan(s_float):
                i_buffer += item_str % ("float", "NaN")
            else:
                i_buffer += item_float % (
                    "float", s_float
                )
        else:
            i_buffer += item_str % ("float", "--")
        if bytes64 is not None:
            d_float = unpack(endian + "d", unhexlify(bytes64))[0]
            if math.isnan(d_float):
                i_buffer += item_str % ("double", "NaN") + nl
            else:
                i_buffer += item_double % (
                    "double", d_float
                ) + nl
        else:
            i_buffer += item_str % ("double", "--") + nl
        if byte8 is not None:
            i_buffer += item_bin % ("binary", '{0:08b}'.format(unpack(endian + "B", unhexlify(byte8))[0])) + nl
        else:
            i_buffer += item_str % ("binary", "--") + nl

        # Update content
        view.set_read_only(False)
        HexInspectGlobal.bfr = i_buffer
        HexInspectGlobal.region = sublime.Region(0, view.size())
        view.run_command("hex_inspector_apply")
        HexInspectGlobal.clear()
        view.set_read_only(True)
        view.sel().clear()

    def is_enabled(self):
        """Check if the command is enabled."""
        return common.is_enabled()

    def run(self, first_byte=None, bytes_wide=None, reset=False):
        """Run the command."""

        self.view = self.window.active_view()
        self.endian = hv_endianness
        byte8, bytes16, bytes32, bytes64 = None, None, None, None
        if not reset and first_byte is not None and bytes_wide is not None:
            byte8, bytes16, bytes32, bytes64 = self.get_bytes(int(first_byte), int(bytes_wide))
        self.display(self.window.get_output_panel('hex_viewer_inspector'), byte8, bytes16, bytes32, bytes64)


def plugin_loaded():
    """Setup plugin."""

    global hv_endianness
    hv_endianness = common.hv_settings("inspector_endian", "little")
