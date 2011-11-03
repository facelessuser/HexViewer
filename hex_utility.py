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

    def highlight_byte(self, view):
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
                        bytes += 1
                elif start != -1:
                    selection.append(sublime.Region(start, loop))
                    start = -1
                    bytes += 1
                if loop == loopend:
                    for item in selection:
                        self.selected_bytes.append(item)
                loop += 1
            if bytes:
                self.ascii_selection(view, first, bytes)

        view.add_regions(
            "hex_view",
            self.selected_bytes,
            'string',
            'dot'
        )
