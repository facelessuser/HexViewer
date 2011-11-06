import sublime
import sublime_plugin
from random import randrange
from os.path import basename
from struct import unpack

HIGHLIGHT_SCOPE = "string"
HIGHLIGHT_ICON = "dot"
HIGHLIGHT_STYLE = "solid"

hv_settings = sublime.load_settings('hex_viewer.sublime-settings')
hv_inspector_enable = hv_settings.get("inspector", False)
hv_endianness = hv_settings.get("inspector_endian", "little")


def is_enabled():
    window = sublime.active_window()
    if window == None:
        return False
    view = window.active_view()
    if view == None:
        return False
    syntax = view.settings().get('syntax')
    language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
    return (language == "hex")


class HexUtilityListenerCommand(sublime_plugin.EventListener):
    def check_debounce(self, debounce_id):
        if self.debounce_id == debounce_id:
            sublime.active_window().run_command('hex_nav')
            self.debounce_id = 0

    def debounce(self):
        # Check if debunce not currently active, or if of same type,
        # but let edit override selection for undos
        debounce_id = randrange(1, 999999)
        self.debounce_id = debounce_id
        sublime.set_timeout(
            lambda: self.check_debounce(debounce_id=debounce_id),
            500
        )

    def on_selection_modified(self, view):
        self.debounce()


class HexNavCommand(sublime_plugin.WindowCommand):
    def init(self):
        init_status = False
        self.address_done = False
        self.total_bytes = 0
        self.address = []
        self.selected_bytes = []

        # Get Seetings from settings file
        group_size = self.view.settings().get("hex_viewer_bits", None)
        self.inspector_enabled = hv_inspector_enable
        self.bytes_wide = self.view.settings().get("hex_viewer_actual_bytes", None)
        self.highlight_scope = hv_settings.get("highlight_scope", HIGHLIGHT_SCOPE)
        self.highlight_icon = hv_settings.get("highlight_icon", HIGHLIGHT_ICON)
        style = hv_settings.get("highlight_style", HIGHLIGHT_STYLE)

        # Process highlight style
        self.highlight_style = 0
        if style == "outline":
            self.highlight_style = sublime.DRAW_OUTLINED
        elif style == "none":
            self.highlight_style = sublime.HIDDEN
        elif style == "underline":
            self.highlight_style = sublime.DRAW_EMPTY_AS_OVERWRITE

        #Process hex grouping
        if group_size != None and self.bytes_wide != None:
            self.group_size = group_size / 8
            init_status = True
        return init_status

    def underline(self):
        # Convert to empty regions
        new_regions = []
        for region in self.selected_bytes:
            start = region.begin()
            end = region.end()
            while start < end:
                new_regions.append(sublime.Region(start))
                start += 1
        self.selected_bytes = new_regions

    def is_enabled(self):
        return is_enabled()

    def get_address(self, start, bytes, line):
        lines = line
        align_to_address_offset = 2
        add_start = lines * self.bytes_wide + start - align_to_address_offset
        add_end = add_start + bytes - 1
        length = len(self.address)
        if length == 0:
            # Add first address group
            multi_byte = -1 if add_start == add_end else add_end
            self.address.append(add_start)
            self.address.append(multi_byte)
        elif (
            (self.address[1] == -1 and self.address[0] + 1 == add_start) or
            (self.address[1] != -1 and self.address[1] + 1 == add_start)
        ):
            # Update end address
            self.address[1] = add_end
        else:
            # Stop getting adresses if bytes are not consecutive
            self.address_done = True

    def display_address(self):
        count = ''
        if self.total_bytes == 0:
            self.view.set_status('hex_address', "Address: None")
            return
        # Display number of bytes whose address is not displayed
        if self.address_done:
            delta = 1 if self.address[1] == -1 else self.address[1] - self.address[0] + 1
            counted_bytes = self.total_bytes - delta
            if counted_bytes > 0:
                count = " [+" + str(counted_bytes) + " bytes]"
        # Display adresses
        status = "Address: "
        if self.address[1] == -1:
            status += ("0x%08x" % self.address[0]) + count
        else:
            status += ("0x%08x" % self.address[0]) + "-" + ("0x%08x" % self.address[1]) + count
        self.view.set_status('hex_address', status)

    def display_total_bytes(self):
        # Display total hex bytes
        self.view.set_status('hex_total_bytes', "Total Bytes: " + str(self.total_bytes))

    def get_byte_count(self, start, end):
        return int((end - start - 1) / (self.group_size * 2 + 1)) * self.group_size + ((end - start - 1) % (self.group_size * 2 + 1)) / 2 + 1

    def hex_selection(self, start, bytes, first_pos):
        offset = 11
        row, column = self.view.rowcol(first_pos)
        #   Calculate byte number              Account for address
        #
        # current_char   wanted_byte
        # ------------ = -----------  => wanted_byte + offset = start_column
        #  total_chars   total_bytes
        #
        start_column = offset + (self.group_size * 2) * start / (self.group_size) + start / (self.group_size)
        # Convert byte column position to test point
        start_byte = self.view.text_point(row, int(start_column))

        # Log first byte
        if self.first_all == -1:
            self.first_all = start_byte

         # Traverse row finding the specified bytes
        highlight_start = -1
        byte_count = bytes
        while byte_count:
            # Byte rising edge
            if self.view.score_selector(start_byte, 'raw.nibble.upper'):
                if highlight_start == -1:
                    highlight_start = start_byte
                start_byte += 2
                byte_count -= 1
                # End of selection
                if byte_count == 0:
                    self.selected_bytes.append(sublime.Region(highlight_start, start_byte))
            else:
                # Byte group falling edge
                self.selected_bytes.append(sublime.Region(highlight_start, start_byte))
                start_byte += 1
                highlight_start = -1
        # Log address
        if bytes and not self.address_done:
            self.get_address(start + 2, bytes, row)

    def ascii_to_hex(self, sel):
        view = self.view
        start = sel.begin()
        end = sel.end()
        bytes = 0
        ascii_range = view.extract_scope(sel.begin())

        # Determine if selection is within ascii range
        if start >= ascii_range.begin() and end <= ascii_range.end() + 1:
            # Single char selection
            if sel.size() == 0:
                bytes = 1
                self.selected_bytes.append(sublime.Region(start, end + 1))
            else:
                # Multi char selection
                bytes = end - start
                self.selected_bytes.append(sublime.Region(start, end))
            self.total_bytes += bytes
            # Highlight hex values
            self.hex_selection(start - ascii_range.begin(), bytes, start)

    def hex_to_ascii(self, sel):
        offset = 11
        bytes = 0
        view = self.view
        start = sel.begin()
        end = sel.end()

        # Get range of hex data
        line = view.line(start)
        hex_chars = int((self.group_size * 2) * self.bytes_wide / (self.group_size) + self.bytes_wide / (self.group_size) + 2)
        hex_range = sublime.Region(
            line.begin() + offset,
            line.begin() + offset + hex_chars
        )

        # Determine if selection is within hex range
        if start >= hex_range.begin() and end <= hex_range.end() + 1:
            # Adjust beginning of selection to begining of first selected byte
            if self.view.score_selector(start, 'raw.nibble.upper') == 0:
                if self.view.score_selector(start, 'raw.nibble.lower'):
                    start -= 1
                elif self.view.score_selector(start + 1, 'raw.nibble.upper') and sel.size() > 0:
                    start += 1
                else:
                    start = None
            # Adjust ending of selection to end of last selected byte
            if sel.size() == 0 and start != None:
                end = start + 2
                bytes = 1
            elif self.view.score_selector(end, 'raw.nibble.upper') == 0:
                if self.view.score_selector(end, 'raw.nibble.lower'):
                    end += 1
                elif self.view.score_selector(end - 1, 'raw.nibble.lower') == 0:
                    end = None
            else:
                end -= 1

            # Highlight hex values and their ascii chars
            if start != None and end != None:
                if bytes == 0:
                    bytes = self.get_byte_count(start, end)
                self.total_bytes += bytes
                # Zero based byte number
                start_byte = self.get_byte_count(hex_range.begin(), start + 2) - 1
                self.hex_selection(start_byte, bytes, start)
                # Highlight Ascii
                ascii_start = hex_range.end() + start_byte
                ascii_end = ascii_start + bytes
                self.selected_bytes.append(sublime.Region(ascii_start, ascii_end))

    def get_highlights(self):
        self.first_all = -1
        for sel in self.view.sel():
            if self.view.score_selector(sel.begin(), 'comment'):
                self.ascii_to_hex(sel)
            else:
                self.hex_to_ascii(sel)

    def run(self):
        view = self.window.active_view()
        self.view = view

        if not self.init():
            return

        self.get_highlights()

        # Show inspector panel
        if self.inspector_enabled:
            reset = False if self.total_bytes == 1 else True
            self.window.run_command(
                'hex_inspector',
                {'first_byte': self.first_all, 'reset': reset, 'bytes_wide': self.bytes_wide}
            )

        # Highlight selected regions
        if self.highlight_style == sublime.DRAW_EMPTY_AS_OVERWRITE:
            self.underline()
        view.add_regions(
            "hex_view",
            self.selected_bytes,
            self.highlight_scope,
            self.highlight_icon,
            self.highlight_style
        )
        # Display selected byte addresses and total bytes selected
        self.display_address()
        self.display_total_bytes()


class HexShowInspectorCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and hv_inspector_enable

    def run(self):
        # Setup inspector window
        view = self.window.get_output_panel('hex_viewer_inspector')
        view.set_syntax_file("Packages/HexViewer/HexInspect.tmLanguage")
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
        self.window.run_command('hex_nav')


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

        # Look for 32 bit worth of bytes
        while start < size and count < 8:
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
            i_buffer += item_float % (
                "float", unpack(endian + "f", bytes32.decode('hex'))[0]
            )
        else:
            i_buffer += item_str % ("float", "--")
        if bytes64 != None:
            i_buffer += item_double % (
                "double", unpack(endian + "d", bytes64.decode('hex'))[0]
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


class HexGoToCommand(sublime_plugin.WindowCommand):
    def go_to_address(self, address):
        #init
        view = self.window.active_view()
        # Adress offset for line
        offset = 11
        group_size = view.settings().get("hex_viewer_bits", None)
        bytes_wide = view.settings().get("hex_viewer_actual_bytes", None)
        if group_size == None and bytes_wide == None:
            return
        group_size = group_size / 8

        # Go to address
        try:
            # Address wanted
            wanted = int(address, 16)
            # Calculate row
            row = int(wanted / (bytes_wide))
            # Byte offset into final row
            byte = wanted % (bytes_wide)
            #   Calculate byte number              Offset Char
            #
            #  wanted_char      byte
            # ------------ = -----------  => wanted_char + 11 = column
            #  total_chars   total_bytes
            #
            column = int((float(byte) / group_size) * ((group_size) * 2 + 1)) + offset

            # Go to address and focus
            pt = view.text_point(row, column)
            view.sel().clear()
            view.sel().add(pt)
            view.show_at_center(pt)
            # Highlight
            self.window.run_command('hex_nav')
        except:
            pass

    def is_enabled(self):
        return is_enabled()

    def run(self):
        self.window.show_input_panel(
            "Find: 0x",
            "",
            self.go_to_address,
            None,
            None
        )
