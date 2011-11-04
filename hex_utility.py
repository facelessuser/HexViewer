import sublime
import sublime_plugin
from random import randrange
from os.path import basename

HIGHLIGHT_SCOPE = "entity.name.class"
HIGHLIGHT_ICON = "dot"
HIGHLIGHT_STYLE = "solid"

hv_settings = sublime.load_settings('hex_viewer.sublime-settings')


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
        group_size = self.view.settings().get("hex_viewer_bits", None)
        self.bytes_wide = self.view.settings().get("hex_viewer_actual_bytes", None)
        self.highlight_scope = hv_settings.get("highlight_scope", HIGHLIGHT_SCOPE)
        self.highlight_icon = hv_settings.get("highlight_icon", HIGHLIGHT_ICON)
        style = hv_settings.get("highlight_style", HIGHLIGHT_STYLE)
        self.highlight_style = 0
        if style == "outline":
            self.highlight_style = sublime.DRAW_OUTLINED
        elif style == "none":
            self.highlight_style = sublime.HIDDEN
        elif style == "underline":
            self.highlight_style = sublime.DRAW_EMPTY_AS_OVERWRITE

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
        syntax = self.window.active_view().settings().get('syntax')
        language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
        return (language == "hex")

    def get_address(self, start, bytes, line):
        lines = line
        add_start = lines * self.bytes_wide + start - 1
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

    def ascii_selection(self, start, bytes):
        # Offset of address
        offset = 11
        # Get position of first byte on line
        row, column = self.view.rowcol(start)
        # Get difference of byte group start and current position
        pos_in_group = (start - self.view.extract_scope(start).a)
        #   Calculate byte number                 Round up
        #
        # current_char   wanted_byte
        # ------------ = -----------  => wanted_byte + 1.5 = start_byte
        #  total_chars   total_bytes
        #
        start_byte = int(((float(column) - offset) - pos_in_group) / ((self.group_size) * 2 + 1) * (self.group_size) + 1.5)
        # Translate the byte to position in ascii column                        Offset into ascii column
        #
        # address_offset + chars_in_bytes + spaces = start_ascii_char => start_ascii_char + start_byte = start_char
        #
        start_char = self.view.text_point(row, int(offset + self.bytes_wide * 2 + self.bytes_wide / self.group_size)) + start_byte
        end_char = start_char + bytes
        # Set ascii region to highlight
        self.selected_bytes.append(sublime.Region(start_char, end_char))
        return start_byte, row

    def run(self):
        view = self.window.active_view()
        self.view = view
        if not self.init():
            return

        for sel in view.sel():
            start = -1
            loop = sel.begin()
            loopend = sel.end()
            selection = []
            bytes = 0
            first = -1
            while (
                loop <= loopend and
                (view.score_selector(loop, 'raw') or view.score_selector(loop, 'dump.buffer-end'))
            ):
                if view.score_selector(loop, 'raw.byte'):
                    # Beginning of byte or start of entire selection
                    if start == -1:
                        # Upper nibble
                        if view.score_selector(loop, 'raw.nibble.upper'):
                            start = loop
                            if loop == loopend:
                                selection.append(sublime.Region(start, start + 2))
                                bytes += 1
                        # Lower nibble
                        else:
                            start = loop - 1
                            bytes += 1
                            if loop == loopend:
                                selection.append(sublime.Region(start, start + 2))
                        # Start of entire selection
                        if first == -1:
                            first = start
                    # Upper nibble
                    elif view.score_selector(loop, 'raw.nibble.upper'):
                        if loop == loopend:
                            selection.append(sublime.Region(start, loop))
                    # Lower nibble
                    elif view.score_selector(loop, 'raw.nibble.lower'):
                        if loop == loopend:
                            selection.append(sublime.Region(start, loop + 1))
                        bytes += 1
                # End of byte
                elif start != -1:
                    selection.append(sublime.Region(start, loop))
                    start = -1
                # Selection end
                if loop == loopend:
                    for item in selection:
                        self.selected_bytes.append(item)
                loop += 1
            # If selecting non-bytes, highlight nothing
            if view.score_selector(loop, 'comment') or view.score_selector(loop, 'keyword'):
                self.selected_bytes = []
                bytes = 0
            # Get addresses
            elif bytes:
                self.total_bytes += bytes
                start_byte, line = self.ascii_selection(first, bytes)
                if not self.address_done:
                    self.get_address(start_byte, bytes, line)
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

        print address

        # Go to address
        try:
            # Address wanted
            wanted = int("0x" + address, 0)
            # Calculate row
            row = int(wanted / (bytes_wide))
            # Byte offset into final row
            byte = wanted % (bytes_wide)

            print "calc"
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
        syntax = self.window.active_view().settings().get('syntax')
        language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
        return (language == "hex")

    def run(self):
        self.window.show_input_panel(
            "Find: 0x",
            "",
            self.go_to_address,
            None,
            None
        )
