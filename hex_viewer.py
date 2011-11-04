import sublime
import sublime_plugin
import struct
from os.path import basename

DEFAULT_BIT_GROUP = 16
DEFAULT_BYTES_WIDE = 24
VALID_BITS = [8, 16, 32, 64, 128]
VALID_BYTES = [8, 10, 16, 24, 32, 48, 64, 128, 256, 512]

hv_settings = sublime.load_settings('hex_viewer.sublime-settings')


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
    def set_format(self):
        self.group_size = DEFAULT_BIT_GROUP / 8
        self.bytes_wide = DEFAULT_BYTES_WIDE

        # Set grouping
        if self.bits in VALID_BITS:
            self.group_size = self.bits / 8

        # Set bytes per line
        if self.bytes in VALID_BYTES:
            self.bytes_wide = self.bytes

        # Check if grouping and bytes per line do not align
        # Round to nearest bytes
        offset = self.bytes_wide % self.group_size
        if offset == self.bytes_wide:
            self.bytes_wide = self.bits / 8
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

    def panel_init(self):
        view = self.window.active_view()
        self.view = self.window.get_output_panel('hex_viewer')
        if view != None and self.view != None:
            # Get font settings
            self.font = hv_settings.get('custom_font', 'None')
            self.font_size = hv_settings.get('panel_custom_font_size', 0)

            # Get file name
            file_name = view.settings().get("hex_viewer_file_name", view.file_name())
            if file_name != None:
                self.view.settings().set("hex_viewer_file_name", file_name)

            # Get current bit and byte settings for Hex View Panel
            self.bits = hv_settings.get('panel_group_bytes_by_bits', DEFAULT_BIT_GROUP)
            self.bytes = hv_settings.get('panel_bytes_per_line', DEFAULT_BYTES_WIDE)
            self.set_format()
        return file_name

    def read_bin(self, file_name, apply_to_current=False):
        count = 0
        line = 0
        group = 0
        p_buffer = ""
        b_buffer = ""
        with open(file_name, "rb") as bin:
            byte = bin.read(1)
            while byte != "":
                count += 1
                group += 1

                # Convert to decimal value
                value = struct.unpack('=B', byte)[0]
                # Save printable value
                p_buffer += "." if value < 32 or value > 126 else byte
                # Add line number
                if count == 1:
                    b_buffer += "%08x:  " % (line * self.bytes_wide)
                # Save hex value
                b_buffer += "%02x" % value

                # Insert space between byte groups
                if (group == self.group_size):
                    b_buffer += " "
                    group = 0

                # Append printable chars and add new line
                if count == self.bytes_wide:
                    b_buffer += " " + p_buffer + "\n"
                    p_buffer = ""
                    line += 1
                    count = 0

                # Get next byte
                byte = bin.read(1)

            # Append printable chars to incomplete line
            if count != 0:
                delta = self.bytes_wide - count
                group_space = delta / self.group_size
                extra_space = delta % self.group_size

                # Add space for missing bytes
                while delta:
                    b_buffer += "  "
                    delta -= 1
                # Add trailing space for missing groups
                while group_space:
                    b_buffer += " "
                    group_space -= 1
                # Add trailing space for incomplete group
                if extra_space:
                    b_buffer += " "
                # Append printable chars
                b_buffer += " " + p_buffer

            # Show binary data
            if apply_to_current:
                view = self.view
            else:
                view = self.window.new_file()
                view.set_name(basename(file_name) + ".hex")
                self.window.focus_view(self.view)
                self.window.run_command("close_file")
                self.window.focus_view(view)

            # Set font
            if self.font != 'None':
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
            view.replace(edit, content_buffer, b_buffer)
            view.end_edit(edit)
            view.set_read_only(True)
            view.set_syntax_file("Packages/HexViewer/Hex.tmLanguage")
            view.sel().clear()
            view.sel().add(sublime.Region(0, 0))

    def read_file(self, file_name):
        view = self.window.open_file(file_name)
        self.window.focus_view(self.view)
        self.window.run_command("close_file")
        self.window.focus_view(view)

    def run(self, bits=None, bytes=None, use_buffer=True):
        # See if output is wanted in a panel or in a buffer
        file_name = self.buffer_init(bits, bytes) if use_buffer else self.panel_init()

        if file_name != None:
            # Decide whether to read in as a binary file or a traditional file
            if self.view.settings().has("hex_viewer_file_name") or not use_buffer:
                if bits == None and bytes == None and use_buffer:
                    # Switch back to traditional output
                    self.read_file(file_name)
                else:
                    # Change format of currently open hex view
                    # Make writable for modification
                    self.view.set_read_only(False)
                    self.read_bin(file_name, True)

                     # Show panel if required
                    if not use_buffer:
                        self.window.run_command("show_panel", {"panel": "output.hex_viewer"})
            else:
                # We are going to swap out the current file for hex output
                # So as not to clutter the screen.  Changes need to be saved
                # Or they will be lost
                if self.view.is_dirty():
                    sublime.error_message(
                        "You have unsaved changes that will be lost! Please save before converting to hex."
                    )
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
        syntax = self.window.active_view().settings().get('syntax')
        language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
        return (language == "hex")

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
