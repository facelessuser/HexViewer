"""
Hex Viewer.

Licensed under MIT
Copyright (c) 2011-2020 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime_plugin
from . import hex_common as common
from .hex_notify import error


class HexFinderCommand(sublime_plugin.WindowCommand):
    """Find the desired address in the hex view."""

    handshake = -1

    def go_to_address(self, address):
        """Go to the specified address."""

        view = self.window.active_view()

        if self.handshake != -1 and self.handshake == view.id():
            # Adress offset for line
            address_offset = view.settings().get('hex_viewer_starting_address', 0)
            group_size = view.settings().get("hex_viewer_bits", None)
            bytes_wide = view.settings().get("hex_viewer_actual_bytes", None)
            if group_size is None and bytes_wide is None:
                return
            group_size = group_size / common.BITS_PER_BYTE

            # Go to address
            try:
                # Address wanted
                wanted = int(address, 16) - address_offset
                assert wanted >= 0, "Address does not exist!"
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
                column = int((float(byte) / group_size) * ((group_size) * 2 + 1)) + common.ADDRESS_OFFSET

                # Go to address and focus
                pt = view.text_point(row, column)
                view.sel().clear()
                view.sel().add(pt)
                view.show_at_center(pt)
                # Highlight
                self.window.run_command('hex_highlighter')
            except Exception:
                pass
        else:
            error("Hex view is no longer in focus! Find address canceled.")
        self.reset()

    def reset(self):
        """Reset."""

        self.handshake = -1

    def is_enabled(self):
        """Check if command is enabled."""
        return common.is_enabled()

    def run(self):
        """Run command."""

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
