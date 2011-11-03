import sublime
import sublime_plugin
from random import randrange


class HexNavCommand(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        self.debounce()

    def check_debounce(self, debounce_id):
        if self.debounce_id == debounce_id:
            self.highlight_byte(sublime.active_window().active_view())
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

    # def get_address(self, view, start, end, line):
    #     lines = line
    #     add_start = lines*self.bytes_wide + start - 1
    #     add_end = lines*self.bytes_wide + end - 1
    #     length = len(self.address)
    #     if length != 0  and (self.address[length - 1][0] + 1) == add_start:
    #         self.address[length - 1][1] = add_end
    #     else:
    #         if add_start != add_end:
    #             self.address.append([add_start, -1])
    #         else:
    #             self.address.append([add_start, add_end])
    #     # Debug
    #     if add_end != add_start:
    #         print ("%08x " % add_start) + (" %08x " % add_end)
    #     else:
    #         print ("%08x " % add_start)

    def ascii_selection(self, view, start, bytes):
        # Offset of address
        offset = 11
        # Get position of first byte on line
        row, column = view.rowcol(start)
        # Get difference of byte group start and current position
        z = (start - view.extract_scope(start).a)
        # Calculate byte number
        start_byte = int(((float(column) - offset) - z) / ((self.group_size) * 2 + 1) * (self.group_size) + 1.5)
        # Translate the byte to position in ascii column
        start_char = view.text_point(row, int(offset + self.bytes_wide*2 + self.bytes_wide/self.group_size)) + start_byte
        end_char = start_char + bytes
        # Set ascii region to highlight
        self.selected_bytes.append(sublime.Region(start_char, end_char))
        return start_byte, start_byte + bytes - 1, row

    def highlight_byte(self, view):
        self.address = []
        self.selected_bytes = []
        group_size = view.settings().get("hex_viewer_bits", None)
        self.bytes_wide = view.settings().get("hex_viewer_actual_bytes", None)
        if group_size != None and self.bytes_wide != None:
            self.group_size = group_size / 8
        else:
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
                    if start == -1:
                        if view.score_selector(loop, 'raw.nibble.upper'):
                            start = loop
                            if loop == loopend:
                                selection.append(sublime.Region(start, start + 2))
                                bytes += 1
                        else:
                            start = loop - 1
                            bytes += 1
                            if loop == loopend:
                                selection.append(sublime.Region(start, start + 2))
                        if first == -1:
                            first = start
                    elif view.score_selector(loop, 'raw.nibble.upper'):
                        if loop == loopend:
                            selection.append(sublime.Region(start, loop))
                    elif view.score_selector(loop, 'raw.nibble.lower'):
                        selection.append(sublime.Region(start, loop + 1))
                        bytes += 1
                elif start != -1:
                    selection.append(sublime.Region(start, loop))
                    start = -1
                if loop == loopend:
                    for item in selection:
                        self.selected_bytes.append(item)
                loop += 1
            if bytes:
                start_byte, end_byte, line = self.ascii_selection(view, first, bytes)
                # self.get_address(view, start_byte, end_byte, line)

        view.add_regions(
            "hex_view",
            self.selected_bytes,
            'string',
            'dot'
        )
