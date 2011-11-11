'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
from hex_common import *


class HexFinderCommand(sublime_plugin.WindowCommand):
    handshake = -1

    def go_to_address(self, address):
        #init
        view = self.window.active_view()

        if self.handshake != -1 and self.handshake == view.id():
            # Adress offset for line
            group_size = view.settings().get("hex_viewer_bits", None)
            bytes_wide = view.settings().get("hex_viewer_actual_bytes", None)
            if group_size == None and bytes_wide == None:
                return
            group_size = group_size / BITS_PER_BYTE

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
                column = int((float(byte) / group_size) * ((group_size) * 2 + 1)) + ADDRESS_OFFSET

                # Go to address and focus
                pt = view.text_point(row, column)
                view.sel().clear()
                view.sel().add(pt)
                view.show_at_center(pt)
                # Highlight
                self.window.run_command('hex_highlighter')
            except:
                pass
        else:
            sublime.error_message("Hex view is no longer in focus! Find address canceled.")
        self.reset()

    def reset(self):
        self.handshake = -1

    def is_enabled(self):
        return is_enabled()

    def run(self):
         # Identify view
        view = self.window.active_view()
        if self.handshake != -1 and self.handshake == view.id():
            self.reset()
        self.handshake = view.id()

        self.window.show_input_panel(
            "Find: 0x",
            "",
            self.go_to_address,
            None,
            None
        )
