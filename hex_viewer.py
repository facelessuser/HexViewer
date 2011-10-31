import sublime
import sublime_plugin
import struct
from os.path import basename

DEFAULT_BIT_GROUP = 32
DEFAULT_BYTES_WIDE = 16
VALID_BITS = [8, 16, 32, 64, 128]
VALID_BYTES = [8, 10, 16, 24, 32, 48, 64, 128, 256, 512]

hv_settings = sublime.load_settings('hex_viewer.sublime-settings')


class HexListenerCommand(sublime_plugin.EventListener):
    def intercept_save_msg(self):
        sublime.status_message("Save intercepted: original content restored.")

    def on_pre_save(self, view):
        # Protect on save: Don't save hex output to file
        file_name = view.file_name()
        self.syntax = view.settings().get('syntax')
        language = basename(self.syntax).replace('.tmLanguage', '').lower() if self.syntax != None else self.syntax
        if file_name != None:
            if language == "hex":
                # See if you have the original buffer
                orig_buffer = view.settings().get("hex_view_file", None)
                if orig_buffer != None:
                    # Clean up buffer in memory
                    view.settings().erase("hex_view_file")
                    view.settings().erase("hex_view_bits")
                    view.settings().erase("hex_view_bytes")
                    # Make view writable again
                    view.set_scratch(False)
                    view.set_read_only(False)
                    # Copy original buffer back in the view
                    current_buffer = sublime.Region(0, view.size())
                    edit = view.begin_edit()
                    view.replace(edit, current_buffer, orig_buffer['hex_buffer'])
                    view.end_edit(edit)
                    # Set original syntax highlighting
                    view.set_syntax_file(orig_buffer['hex_syntax'])
                    # Notify user of interception
                    sublime.set_timeout(lambda: self.intercept_save_msg(), 1000)


class HexViewerCommand(sublime_plugin.TextCommand):
    def init(self, bits, bytes, new_file):
        self.new_file = new_file
        # Get current bit and byte settings from view
        # Or try and get them from settings file
        #If none are found, use default
        current_bits = self.view.settings().get(
            'hex_view_bits',
            hv_settings.get('group_bytes_by_bits', DEFAULT_BIT_GROUP)
        )
        current_bytes = self.view.settings().get(
            'hex_view_bytes',
            hv_settings.get('bytes_per_line', DEFAULT_BYTES_WIDE)
        )
        # Use passed in bit and byte settings if available
        self.bits = bits if bits != None else int(current_bits)
        self.bytes = bytes if bytes != None else int(current_bytes)
        self.group_size = DEFAULT_BIT_GROUP / 8
        self.bytes_wide = DEFAULT_BYTES_WIDE

        # Set grouping
        if self.bits in VALID_BITS:
            self.group_size = self.bits / 8

        # Set bytes per line
        if self.bytes in VALID_BYTES:
            #Account for byte grouping that doesn't line up
            self.bytes_wide = self.bytes

        # Check if grouping and bytes per line do not align
        # Round down to nearest bytes
        offset = self.bytes_wide % self.group_size
        if offset == self.bytes_wide:
            self.bytes_wide = self.bits / 8
        elif offset != 0:
            self.bytes_wide -= offset

    def read_bin(self, file_name, edit):
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

                # Add missing bytes
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
            view = self.view.window().new_file() if self.new_file else self.view
            content_buffer = sublime.Region(0, view.size())
            # Save original buffer to protect against saves
            # while in hex view mode
            self.view.settings().set("hex_view_bits", self.bits)
            self.view.settings().set("hex_view_bytes", self.bytes)
            if not self.new_file and not self.view.settings().has("hex_view_file"):
                self.view.settings().set(
                    "hex_view_file",
                    {
                        "hex_syntax": self.syntax,
                        "hex_buffer": self.view.substr(content_buffer)
                    }
                )
            view.set_scratch(True)
            view.replace(edit, content_buffer, b_buffer)
            view.set_read_only(True)
            view.set_syntax_file("Packages/HexViewer/Hex.tmLanguage")

    def restore_buffer(self, file_name, edit):
        window = sublime.active_window()
        window.run_command("close_file")
        window.open_file(file_name)

    def run(self, edit, new_file=False, bits=None, bytes=None):
        self.view = sublime.active_window().active_view()
        self.init(bits, bytes, new_file)
        file_name = self.view.file_name()
        self.syntax = self.view.settings().get('syntax')
        language = basename(self.syntax).replace('.tmLanguage', '').lower() if self.syntax != None else self.syntax
        if file_name != None:
            if language == "hex" and new_file == False:
                if bits == None and bytes == None:
                    self.restore_buffer(file_name, edit)
                else:
                    self.view.set_read_only(False)
                    self.read_bin(file_name, edit)
            else:
                if self.view.is_dirty():
                    sublime.error_message(
                        "You have unsaved changes that will be lost! Please save before converting to hex."
                    )
                else:
                    self.read_bin(file_name, edit)


class HexViewerOptionsCommand(sublime_plugin.WindowCommand):
    def set_bits(self, value):
        if value != -1:
            self.window.active_view().run_command('hex_viewer', {"bits": VALID_BITS[value]})

    def set_bytes(self, value):
        if value != -1:
            self.window.active_view().run_command('hex_viewer', {"bytes": VALID_BYTES[value]})

    def run(self, option):
        self.view = self.window.active_view()
        file_name = self.view.file_name()
        self.syntax = self.view.settings().get('syntax')
        language = basename(self.syntax).replace('.tmLanguage', '').lower() if self.syntax != None else self.syntax
        if file_name != None:
            if language == "hex":
                option_list = []
                if option == "bits":
                    for bits in VALID_BITS:
                        option_list.append(str(bits) + " bits")
                    self.window.show_quick_panel(option_list, self.set_bits)
                elif option == "bytes":
                    for bytes in VALID_BYTES:
                        option_list.append(str(bytes) + " bytes")
                    self.window.show_quick_panel(option_list, self.set_bytes)
