'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
import struct
from os.path import basename
from hex_common import *

DEFAULT_BIT_GROUP = 16
DEFAULT_BYTES_WIDE = 24
VALID_BITS = [8, 16, 32, 64, 128]
VALID_BYTES = [8, 10, 16, 24, 32, 48, 64, 128, 256, 512]


def iterfile(filename, groupsize, maxblocksize=4096):
    with open(filename, "rb") as bin:
        # Ensure read block is a multiple of groupsize
        blocksize = maxblocksize - (maxblocksize % groupsize)

        start = 0
        bytes = bin.read(blocksize)
        while bytes:
            outbytes = bytes[start:start + groupsize]
            while outbytes:
                yield outbytes
                start += groupsize
                outbytes = bytes[start:start + groupsize]
            start = 0
            bytes = bin.read(blocksize)


class HexViewerListenerCommand(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        # We are saving the file so it will now reference itself
        # Instead of the original binary file, so reset settings.
        # Hex output will no longer be able to toggle back
        # To original file, so open original file along side
        # Newly saved hex output
        if view.settings().has("hex_viewer_file_name"):
            view.window().open_file(view.settings().get("hex_viewer_file_name"))
            view.set_scratch(False)
            view.set_read_only(False)
            view.settings().erase("hex_viewer_bits")
            view.settings().erase("hex_viewer_bytes")
            view.settings().erase("hex_viewer_actual_bytes")
            view.settings().erase("hex_viewer_file_name")


class HexViewerCommand(sublime_plugin.WindowCommand):
    handshake = -1
    file_name = ""

    def set_format(self):
        self.group_size = DEFAULT_BIT_GROUP / BITS_PER_BYTE
        self.bytes_wide = DEFAULT_BYTES_WIDE

        # Set grouping
        if self.bits in VALID_BITS:
            self.group_size = self.bits / BITS_PER_BYTE

        # Set bytes per line
        if self.bytes in VALID_BYTES:
            self.bytes_wide = self.bytes

        # Check if grouping and bytes per line do not align
        # Round to nearest bytes
        offset = self.bytes_wide % self.group_size
        if offset == self.bytes_wide:
            self.bytes_wide = self.bits / BITS_PER_BYTE
        elif offset != 0:
            self.bytes_wide -= offset

    def buffer_init(self, bits, bytes):
        self.view = self.window.active_view()
        file_name = None
        if self.view != None:
            # Get font settings
            self.font = hv_settings.get('custom_font', 'None')
            self.font_size = hv_settings.get('custom_font_size', 0)

            #Get file name
            file_name = self.view.settings().get("hex_viewer_file_name", self.view.file_name())

            # Get current bit and byte settings from view
            # Or try and get them from settings file
            # If none are found, use default
            current_bits = self.view.settings().get(
                'hex_viewer_bits',
                hv_settings.get('group_bytes_by_bits', DEFAULT_BIT_GROUP)
            )
            current_bytes = self.view.settings().get(
                'hex_viewer_bytes',
                hv_settings.get('bytes_per_line', DEFAULT_BYTES_WIDE)
            )
            # Use passed in bit and byte settings if available
            self.bits = bits if bits != None else int(current_bits)
            self.bytes = bytes if bytes != None else int(current_bytes)
            self.set_format()
        return file_name

    def read_bin(self, file_name, apply_to_current=False):
        translate_table = ("." * 32) + "".join(chr(c) for c in xrange(32, 127)) + ("." * 129)
        def_struct = struct.Struct("=" + ("B" * self.bytes_wide))
        def_template = (("%02x" * self.group_size) + " ") * (self.bytes_wide / self.group_size)

        line = 0
        b_buffer = []
        for bytes in iterfile(file_name, self.bytes_wide):
            l_buffer = []

            # Add line number
            l_buffer.append("%08x:  " % (line * self.bytes_wide))

            try:
                # Complete line
                # Convert to decimal value
                values = def_struct.unpack(bytes)

                # Add hex value
                l_buffer.append(def_template % values)
            except struct.error:
                # Incomplete line
                # Convert to decimal value
                values = struct.unpack("=" + ("B" * len(bytes)), bytes)

                # Add hex value
                remain_group = len(bytes) / self.group_size
                remain_extra = len(bytes) % self.group_size
                l_buffer.append(((("%02x" * self.group_size) + " ") * (remain_group) + ("%02x" * remain_extra)) % values)

                # Append printable chars to incomplete line
                delta = self.bytes_wide - len(bytes)
                group_space = delta / self.group_size
                extra_space = (1 if delta % self.group_size else 0)

                l_buffer.append(" " * (group_space + extra_space + delta * 2))

            # Append printable chars
            l_buffer.append(" :" + bytes.translate(translate_table))

            # Add line to buffer
            b_buffer.append("".join(l_buffer))

            line += 1

        # Join buffer lines
        b_buffer = "\n".join(b_buffer)

        # Show binary data
        if apply_to_current:
            view = self.view
        else:
            view = self.window.new_file()
            view.set_name(basename(file_name) + ".hex")
            self.window.focus_view(self.view)
            self.window.run_command("close_file")
            self.window.focus_view(view)

        # Set syntax
        view.set_syntax_file("Packages/HexViewer/Hex.tmLanguage")

        # Set font
        if self.font != 'none':
            view.settings().set('font_face', self.font)
        if self.font_size != 0:
            view.settings().set("font_size", self.font_size)

        # Get buffer size
        content_buffer = sublime.Region(0, view.size())

        # Save hex view settings
        view.settings().set("hex_viewer_bits", self.bits)
        view.settings().set("hex_viewer_bytes", self.bytes)
        view.settings().set("hex_viewer_actual_bytes", self.bytes_wide)
        if not self.view.settings().has("hex_viewer_file_name"):
            view.settings().set("hex_viewer_file_name", file_name)

        # Show hex content in view; make read only
        view.set_scratch(True)
        edit = view.begin_edit()
        view.sel().clear()
        view.replace(edit, content_buffer, b_buffer)
        view.end_edit(edit)
        view.set_read_only(True)
        # Offset past address to first byte
        view.sel().add(sublime.Region(ADDRESS_OFFSET, ADDRESS_OFFSET))
        if hv_settings.get("inspector", False) and hv_settings.get("inspector_auto_show", False):
            view.window().run_command("hex_show_inspector")

    def read_file(self, file_name):
        if hv_settings.get("inspector", False):
            self.window.run_command("hex_hide_inspector")
        view = self.window.open_file(file_name)
        self.window.focus_view(self.view)
        self.window.run_command("close_file")
        self.window.focus_view(view)

    def discard_changes(self, value):
        if value.strip().lower() == "yes":
            if self.switch_type == "hex":
                view = sublime.active_window().active_view()
                if self.handshake == view.id():
                    self.view.set_read_only(False)
                    self.view.set_scratch(True)
                    clear_edits(self.view)
                    self.read_bin(self.file_name, self.apply_self)
                else:
                    sublime.error_message("Target view is no longer in focus!  Hex view aborted.")
            else:
                clear_edits(self.view)
                self.read_file(self.file_name)
        self.reset()

    def discard_panel(self):
        self.window.show_input_panel(
            "Discard Changes? (yes | no):",
            "no",
            self.discard_changes,
            None,
            self.reset
        )

    def reset(self):
        self.handshake = -1
        self.file_name = ""
        self.type = None
        self.apply_self = False

    def run(self, bits=None, bytes=None):
        # Init Buffer
        file_name = self.buffer_init(bits, bytes)

        # Identify view
        if self.handshake != -1 and self.handshake == self.view.id():
            self.reset()
        self.handshake = self.view.id()

        if file_name != None:
            # Decide whether to read in as a binary file or a traditional file
            if self.view.settings().has("hex_viewer_file_name"):
                self.view_type = "hex"
                if is_hex_dirty(self.view):
                    self.file_name = file_name
                    if bits == None and bytes == None:
                        self.switch_type = "file"
                    else:
                        self.switch_type = "hex"
                        self.apply_self = True
                    self.discard_panel()
                else:
                    if bits == None and bytes == None:
                        # Switch back to traditional output
                        self.read_file(file_name)
                    else:
                        # Change format of currently open hex view
                        # Make writable for modification
                        self.view.set_read_only(False)
                        self.read_bin(file_name, True)
            else:
                # We are going to swap out the current file for hex output
                # So as not to clutter the screen.  Changes need to be saved
                # Or they will be lost
                if self.view.is_dirty():
                    self.file_name = file_name
                    self.switch_type = "hex"
                    self.apply_self = False
                    self.discard_panel()
                else:
                    # Switch to hex output
                    self.read_bin(file_name)


class HexViewerOptionsCommand(sublime_plugin.WindowCommand):
    def set_bits(self, value):
        if value != -1:
            self.window.run_command('hex_viewer', {"bits": VALID_BITS[value]})

    def set_bytes(self, value):
        if value != -1:
            self.window.run_command('hex_viewer', {"bytes": VALID_BYTES[value]})

    def is_enabled(self):
        return is_enabled()

    def run(self, option):
        self.view = self.window.active_view()
        file_name = self.view.settings().get("hex_viewer_file_name", self.view.file_name())
        if file_name != None:
            if self.view.settings().has("hex_viewer_file_name"):
                option_list = []
                if option == "bits":
                    for bits in VALID_BITS:
                        option_list.append(str(bits) + " bits")
                    self.window.show_quick_panel(option_list, self.set_bits)
                elif option == "bytes":
                    for bytes in VALID_BYTES:
                        option_list.append(str(bytes) + " bytes")
                    self.window.show_quick_panel(option_list, self.set_bytes)
