import sublime
import sublime_plugin
import struct
from os.path import basename

BYTE_GROUP = 32
BYTES_WIDE = 16

hv_settings = sublime.load_settings('hex_viewer.sublime-settings')


class HexListenerCommand(sublime_plugin.EventListener):
    def intercept_save_msg(self):
        sublime.status_message("Save intercepted: original content restored.")

    def on_pre_save(self, view):
        # Protect on save: Don't save hex output to file
        file_name = view.file_name()
        self.syntax = view.settings().get('syntax')
        language = basename(self.syntax).replace('.tmLanguage', '').lower() if self.syntax != None else self.syntax
        if(file_name != None):
            if(language == "hex"):
                view_id = str(view.id())
                # See if you have the original buffer
                orig_buffer = view.settings().get("hex_view_" + view_id, None)
                if orig_buffer != None:
                    # Clean up buffer in memory
                    view.settings().erase("hex_view_" + view_id)
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
    def init(self):
        byte_group = hv_settings.get('group_bytes_by_bits', BYTE_GROUP)
        bytes_wide = hv_settings.get('bytes_per_line', BYTES_WIDE)
        self.group_size = None
        self.bytes_wide = None

        # Set grouping
        if (
            byte_group == 8 or
            byte_group == 16 or
            byte_group == 32 or
            byte_group == 64
        ):
            self.group_size = byte_group / 8

        # Set bytes per line
        if (
            bytes_wide == 8 or
            bytes_wide == 16 or
            bytes_wide == 32 or
            bytes_wide == 64
        ):
            self.bytes_wide = bytes_wide

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
            if not self.new_file:
                view_id = str(self.view.id())
                self.view.settings().set(
                    "hex_view_" + view_id,
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
        # This method keeps from having to reopen the original file
        # But this always leaves the buffer dirty.
        # Could be fixed by saving after switch, but I don't like
        # saving when not needed.
        # self.id = str(self.view.id())
        # hex_view = self.view.settings().get("hex_view_" + self.id, None)
        # if hex_view != None:
        #     content_buffer = sublime.Region(0, self.view.size())
        #     self.view.set_read_only(False)
        #     self.view.replace(edit, content_buffer, hex_view['hex_buffer'])
        #     self.view.set_syntax_file(hex_view['hex_syntax'])
        #     self.view.settings().erase("hex_view_" + self.id)
        #     self.view.set_scratch(False)

    def run(self, edit, new_file=False):
        self.init()
        self.view = sublime.active_window().active_view()
        file_name = self.view.file_name()
        self.syntax = self.view.settings().get('syntax')
        language = basename(self.syntax).replace('.tmLanguage', '').lower() if self.syntax != None else self.syntax
        if(file_name != None):
            if(language == "hex" and new_file == False):
                self.restore_buffer(file_name, edit)
            else:
                if self.view.is_dirty():
                    sublime.error_message(
                        "You have unsaved changes that will be lost! Please save before converting to hex."
                    )
                else:
                    self.new_file = new_file
                    self.read_bin(file_name, edit)
