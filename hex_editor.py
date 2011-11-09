import sublime
import sublime_plugin
import re
from struct import unpack
from hex_common import *

HIGHLIGHT_EDIT_SCOPE = "keyword"
HIGHLIGHT_EDIT_ICON = "none"
HIGHLIGHT_EDIT_STYLE = "underline"


class HexDiscardEditsCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled() and len(self.window.active_view().get_regions("hex_edit"))

    def run(self):
        view = self.window.active_view()
        group_size = int(view.settings().get("hex_viewer_bits", None))
        bytes_wide = int(view.settings().get("hex_viewer_actual_bytes", None))
        clear_edits(view)
        self.window.run_command('hex_viewer', {"bits": group_size, "bytes": bytes_wide})


class HexEditorCommand(sublime_plugin.WindowCommand):
    handshake = -1

    def init(self):
        init_status = False

        # Get highlight settings
        self.highlight_scope = hv_settings.get("highlight_edit_scope", HIGHLIGHT_EDIT_SCOPE)
        self.highlight_icon = hv_settings.get("highlight_edit_icon", HIGHLIGHT_EDIT_ICON)
        style = hv_settings.get("highlight_edit_style", HIGHLIGHT_EDIT_STYLE)

        # No icon?
        if self.highlight_icon == "none":
            self.highlight_icon = ""

        # Process highlight style
        self.highlight_style = 0
        if style == "outline":
            self.highlight_style = sublime.DRAW_OUTLINED
        elif style == "none":
            self.highlight_style = sublime.HIDDEN
        elif style == "underline":
            self.highlight_style = sublime.DRAW_EMPTY_AS_OVERWRITE

        # Get Seetings from settings file
        group_size = self.view.settings().get("hex_viewer_bits", None)
        self.bytes_wide = self.view.settings().get("hex_viewer_actual_bytes", None)
        #Process hex grouping
        if group_size != None and self.bytes_wide != None:
            self.group_size = group_size / BITS_PER_BYTE
            init_status = True
        return init_status

    def is_enabled(self):
        return is_enabled()

    def apply_edit(self, value):
        edits = ""
        self.view = self.window.active_view()
        # Is this the same view as earlier?
        if self.handshake != -1 and self.handshake == self.view.id():
            total_chars = self.total_bytes * 2
            selection = self.line["selection"]

            # Transform string if provided
            if re.match("^s\:", value) != None:
                edits = value[2:len(value)].encode("hex")
            else:
                edits = value.strip().replace(" ", "").lower()

            # See if change occured and if changes are valid
            if len(edits) != total_chars:
                sublime.error_message("Expected %d byte(s) of data, but recieved %d!" % (self.total_bytes, len(edits) * 2))
            elif re.match("[\da-f]{" + str(total_chars) + "}", edits) == None:
                sublime.error_message("Request contains invalid data!")
            elif selection != edits:
                # Get previous dirty markers before modifying buffer
                regions = self.view.get_regions("hex_edit")

                # Construct old and new data for diffs
                edits = self.line["data1"] + edits + self.line["data2"]
                original = self.line["data1"] + selection + self.line["data2"]

                # Initialize
                ascii = " :"
                start = 0
                ascii_start_pos = self.ascii_pos
                hex_start_pos = self.line["range"].begin() + ADDRESS_OFFSET
                end = len(edits)
                count = 1
                change_start = None

                # Reconstruct line
                l_buffer = self.line["address"]
                while start < end:
                    byte_end = start + 2
                    value = edits[start:byte_end]

                    # Diff data and mark changed bytes
                    if value != original[start:byte_end]:
                        if change_start == None:
                            change_start = [hex_start_pos, ascii_start_pos]
                    elif change_start != None:
                        if self.view.score_selector(hex_start_pos - 1, 'raw.nibble.lower'):
                            regions.append(sublime.Region(change_start[0], hex_start_pos))
                        else:
                            regions.append(sublime.Region(change_start[0], hex_start_pos - 1))
                        regions.append(sublime.Region(change_start[1], ascii_start_pos))
                        change_start = None

                    # Write bytes and add space and at group region end
                    l_buffer += value
                    if count == self.group_size:
                        l_buffer += " "
                        hex_start_pos += 1
                        count = 0

                    # Copy valid printible ascii chars over or substitute with "."
                    dec = unpack("=B", value.decode("hex"))[0]
                    ascii += chr(dec) if dec in xrange(32, 127) else "."
                    start += 2
                    count += 1
                    hex_start_pos += 2
                    ascii_start_pos += 1

                # Check for end of line case for highlight
                if change_start != None:
                    regions.append(sublime.Region(change_start[0], hex_start_pos))
                    regions.append(sublime.Region(change_start[1], ascii_start_pos))
                    change_start = None

                # Append ascii chars to line accounting for missing bytes in line
                delta = int(self.bytes_wide) - len(edits) / 2
                group_space = int(delta / self.group_size) + (1 if delta % self.group_size else 0)
                l_buffer += " " * (group_space + delta * 2) + ascii

                # Apply buffer edit
                self.view.sel().clear()
                self.view.set_read_only(False)
                edit = self.view.begin_edit()
                self.view.replace(edit, self.line["range"], l_buffer)
                self.view.end_edit(edit)
                self.view.set_read_only(True)
                self.view.sel().add(sublime.Region(self.start_pos, self.end_pos))

                # Underline if required
                if self.highlight_style == sublime.DRAW_EMPTY_AS_OVERWRITE:
                    regions = underline(regions)

                # Highlight changed bytes
                self.view.add_regions(
                    "hex_edit",
                    regions,
                    self.highlight_scope,
                    self.highlight_icon,
                    self.highlight_style
                )

                # Update selection
                self.window.run_command('hex_highlighter')
        else:
            sublime.error_message("Hex view is no longer in focus! Edit Failed.")
        # Clean up
        self.reset()

    def reset(self):
        self.handshake = -1
        self.total_bytes = 0
        self.start_pos = -1
        self.end_pos = -1
        self.line = {}

    def ascii_to_hex(self, start, end):
        bytes = 0
        size = end - start
        ascii_range = self.view.extract_scope(start)

        # Determine if selection is within ascii range
        if start >= ascii_range.begin() and end <= ascii_range.end() + 1:
            # Single char selection or multi
            bytes = 1 if size == 0 else end - start

        if bytes != 0:
            row, column = self.view.rowcol(start)
            column = ascii_to_hex_col(column, start - ascii_range.begin(), self.group_size)
            hex_pos = self.view.text_point(row, column)
            start = hex_pos

             # Traverse row finding the specified bytes
            byte_count = bytes
            while byte_count:
                # Byte rising edge
                if self.view.score_selector(hex_pos, 'raw.nibble.upper'):
                    hex_pos += 2
                    byte_count -= 1
                    # End of selection
                    if byte_count == 0:
                        end = hex_pos - 1
                else:
                    hex_pos += 1
        return start, end, bytes

    def run(self):
        self.view = self.window.active_view()

        # Identify view
        if self.handshake != -1 and self.handshake == self.view.id():
            self.reset()
        self.handshake = self.view.id()

        # Single selection?
        if len(self.view.sel()) == 1:
            # Init
            if not self.init():
                self.reset()
                return
            sel = self.view.sel()[0]
            start = sel.begin()
            end = sel.end()
            bytes = 0

            # Get range of hex data
            line = self.view.line(start)
            hex_range = get_hex_range(line, self.group_size, self.bytes_wide)

            if self.view.score_selector(start, "comment"):
                start, end, bytes = self.ascii_to_hex(start, end)

            # Determine if selection is within hex range
            if start >= hex_range.begin() and end <= hex_range.end():
                # Adjust beginning of selection to begining of first selected byte
                if bytes == 0:
                    start, end, bytes = adjust_hex_sel(self.view, start, end, self.group_size)

                # Get general line info for diffing and editing
                if bytes != 0:
                    self.ascii_pos = hex_range.end() + ASCII_OFFSET
                    self.total_bytes = bytes
                    self.start_pos = start
                    self.end_pos = end + 1
                    self.line = {
                        "range": line,
                        "address": self.view.substr(sublime.Region(line.begin(), line.begin() + ADDRESS_OFFSET)),
                        "selection": self.view.substr(sublime.Region(start, end + 1)).strip().replace(" ", ""),
                        "data1": self.view.substr(sublime.Region(hex_range.begin(), start)).strip().replace(" ", ""),
                        "data2": self.view.substr(sublime.Region(end + 1, hex_range.end() + 1)).strip().replace(" ", "")
                    }

                    # Send selected bytes to be edited
                    self.window.show_input_panel(
                        "Edit:",
                        self.view.substr(sublime.Region(start, end + 1)).strip(),
                        self.apply_edit,
                        None,
                        None
                    )
