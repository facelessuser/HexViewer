"""
Hex Viewer.

Licensed under MIT
Copyright (c) 2011-2015 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime
import sublime_plugin
import struct
import threading
from os.path import basename, exists
from os.path import getsize as get_file_size
from os import remove
import HexViewer.hex_common as common
from fnmatch import fnmatch
import tempfile
import subprocess
from HexViewer.hex_notify import notify, error

DEFAULT_BIT_GROUP = 16
DEFAULT_BYTES_WIDE = 24
DEFAULT_MAX_FILE_SIZE = 50000.0
VALID_BITS = [8, 16, 32, 64, 128]
VALID_BYTES = [8, 10, 16, 24, 32, 48, 64, 128, 256, 512]
AUTO_OPEN = False

active_thread = None


class ReadBin(threading.Thread):
    """Read a file in binary mode."""

    def __init__(self, file_name, bytes_wide, group_size, starting_address=0):
        """Initialize."""

        self.starting_address = starting_address
        self.bytes_wide = int(bytes_wide)
        self.group_size = int(group_size)
        self.file_name = file_name
        self.file_size = get_file_size(file_name)
        self.read_count = 0
        self.abort = False
        self.hex_lower = common.use_hex_lowercase()
        threading.Thread.__init__(self)

    def iterfile(self, maxblocksize=4096):
        """Iterate through the file chunking the data in 4096 blocks."""

        with open(self.file_name, "rb") as bin_file:
            # Ensure read block is a multiple of groupsize
            bytes_wide = self.bytes_wide
            blocksize = maxblocksize - (maxblocksize % bytes_wide)

            start = 0
            byte_array = bin_file.read(blocksize)
            while byte_array:
                outbytes = byte_array[start:start + bytes_wide]
                while outbytes:
                    yield outbytes
                    start += bytes_wide
                    outbytes = byte_array[start:start + bytes_wide]
                start = 0
                byte_array = bin_file.read(blocksize)

    def run(self):
        """Run the command."""

        byte_string = "%02x" if self.hex_lower else "%02X"
        address_string = "%08x" if self.hex_lower else "%08X"
        translate_table = str.maketrans(
            "".join([chr(c) for c in range(0, 256)]),
            "".join(["."] * 32 + [chr(c) for c in range(32, 127)] + ["."] * 129)
        )
        def_struct = struct.Struct("=" + ("B" * self.bytes_wide))
        def_template = ((byte_string * self.group_size) + " ") * int(self.bytes_wide / self.group_size)

        line = 0
        read_count = 0
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".hex") as f:
            self.hex_name = f.name
            for byte_array in self.iterfile():
                if self.abort:
                    return
                l_buffer = []

                read_count += self.bytes_wide
                self.read_count = read_count if read_count < self.file_size else self.file_size

                # Add line number
                l_buffer.append((address_string + ":  ") % ((line * self.bytes_wide) + self.starting_address))

                try:
                    # Complete line
                    # Convert to decimal value
                    values = def_struct.unpack(byte_array)

                    # Add hex value
                    l_buffer.append(def_template % values)
                except struct.error:
                    # Incomplete line
                    # Convert to decimal value
                    values = struct.unpack("=" + ("B" * len(byte_array)), byte_array)

                    # Add hex value
                    remain_group = int(len(byte_array) / self.group_size)
                    remain_extra = len(byte_array) % self.group_size
                    l_buffer.append(
                        (
                            ((byte_string * self.group_size) + " ") *
                            (remain_group) + (byte_string * remain_extra)
                        ) % values
                    )

                    # Append printable chars to incomplete line
                    delta = self.bytes_wide - len(byte_array)
                    group_space = int(delta / self.group_size)
                    extra_space = (1 if delta % self.group_size else 0)

                    l_buffer.append(" " * (group_space + extra_space + delta * 2))

                # Append printable chars
                l_buffer.append(" :" + "".join([chr(translate_table[b]) for b in byte_array]))

                # Add line to buffer
                f.write(("\n" if line > 0 else "") + "".join(l_buffer))

                line += 1


class HexViewerListenerCommand(sublime_plugin.EventListener):
    """Hex viewer listener command."""

    open_me = None

    def is_bin_file(self, file_path, encoding):
        """Determine if view is a bin file."""
        match = False
        if not common.hv_settings("disable_auto_open_hex_encoding", False) and encoding == "Hexadecimal":
            match = True
        else:
            patterns = common.hv_settings("auto_open_patterns", [])
            for pattern in patterns:
                match |= fnmatch(file_path, pattern)
                if match:
                    break
        return match

    def open_bin_file(self, view=None, window=None):
        """Logic to open bin file as a hex view."""

        open_now = False
        if view is not None and window is not None:
            # Direct open file
            open_now = True
        else:
            # Preview view of file
            window = sublime.active_window()
            if window is not None:
                view = window.active_view()
        # Open bin file in hex viewer
        if window and view and (open_now or view.file_name() == self.open_me):
            is_preview = window and view.file_name() not in [file.file_name() for file in window.views()]
            if is_preview:
                return
            view.settings().set("hex_no_auto_open", True)
            window.run_command('hex_viewer')

    def auto_load(self, view, window, is_preview):
        """Auto load the hex view."""

        file_name = view.file_name()
        if file_name is not None and not exists(file_name):
            file_name = None
        encoding = view.encoding()
        # Make sure we have a file name and that we haven't already processed the view
        if file_name is not None and not view.settings().get("hex_no_auto_open", False):
            # Make sure the file is specified in our binary file list
            if self.is_bin_file(file_name, encoding):
                # Handle previw or direct open
                if is_preview:
                    self.open_me = file_name
                    sublime.set_timeout(self.open_bin_file, 100)
                else:
                    self.open_me = file_name
                    self.open_bin_file(view, window)

    def on_activated(self, view):
        """Logic for preview windows."""

        if common.hv_settings("auto_open", AUTO_OPEN) and not view.settings().get('is_widget'):
            window = view.window()
            is_preview = window and view.file_name() not in [file.file_name() for file in window.views()]
            if view.settings().get("hex_view_postpone_hexview", True) and not view.is_loading():
                self.auto_load(view, window, is_preview)

    def on_load(self, view):
        """Determine if anything needs to be done with the loaded file."""

        # Logic for direct open files
        if common.hv_settings("auto_open", AUTO_OPEN) and not view.settings().get('is_widget'):
            window = view.window()
            is_preview = window and view.file_name() not in [file.file_name() for file in window.views()]
            if window and not is_preview and view.settings().get("hex_view_postpone_hexview", True):
                self.auto_load(view, window, is_preview)

        temp_file = view.settings().get("hex_viewer_temp_file", None)
        if temp_file is not None:
            if exists(temp_file):
                remove(temp_file)

            view.set_name(basename(view.settings().get("hex_viewer_file_name")) + ".hex")

            view.sel().clear()
            # Offset past address to first byte
            view.sel().add(sublime.Region(common.ADDRESS_OFFSET, common.ADDRESS_OFFSET))
            if common.hv_settings("inspector", False) and common.hv_settings("inspector_auto_show", False):
                window = view.window()
                if window is not None:
                    view.window().run_command("hex_show_inspector")

    def on_pre_save(self, view):
        """
        Upadate on save.

        We are saving the file so it will now reference itself
        Instead of the original binary file, so reset settings.
        Hex output will no longer be able to toggle back
        to the original file, so open original file along side the
        newly saved hex output.
        """

        if view.settings().has("hex_viewer_file_name"):
            view.window().open_file(view.settings().get("hex_viewer_file_name"))
            view.set_scratch(False)
            view.set_read_only(False)
            view.settings().erase("hex_viewer_bits")
            view.settings().erase("hex_viewer_bytes")
            view.settings().erase("hex_viewer_actual_bytes")
            view.settings().erase("hex_viewer_file_name")
            view.settings().erase("hex_viewer_starting_address")


class HexViewerCommand(sublime_plugin.WindowCommand):
    """Hex viewer command."""

    handshake = -1
    file_name = ""
    thread = None

    def set_format(self):
        """Set the hex view format."""

        self.group_size = DEFAULT_BIT_GROUP / common.BITS_PER_BYTE
        self.bytes_wide = DEFAULT_BYTES_WIDE

        # Set grouping
        if self.bits in VALID_BITS:
            self.group_size = self.bits / common.BITS_PER_BYTE

        # Set bytes per line
        if self.bytes in common.hv_settings("valid_bytes_per_line", VALID_BYTES):
            self.bytes_wide = self.bytes

        # Check if grouping and bytes per line do not align
        # Round to nearest bytes
        offset = self.bytes_wide % self.group_size
        if offset == self.bytes_wide:
            self.bytes_wide = self.bits / common.BITS_PER_BYTE
        elif offset != 0:
            self.bytes_wide -= offset

    def buffer_init(self, bits, byte_array):
        """Initialize info for the hex buffer."""
        self.sheet = None
        self.view = self.window.active_view()
        if self.view is None:
            self.sheet = self.window.active_sheet()
            self.id = self.sheet.id()
        else:
            self.id = self.window.active_sheet().id()
        file_name = None
        if self.sheet is not None:
            self.font = common.hv_settings('custom_font', 'none')
            self.font_size = common.hv_settings('custom_font_size', 0)

            file_name = self.window.extract_variables().get('file')
            current_bits = common.hv_settings('group_bytes_by_bits', DEFAULT_BIT_GROUP)
            current_bytes = common.hv_settings('bytes_per_line', DEFAULT_BYTES_WIDE)
            self.bits = bits if bits is not None else int(current_bits)
            self.bytes = byte_array if byte_array is not None else int(current_bytes)
            self.set_format()

        elif self.view is not None:
            # Get font settings
            self.font = common.hv_settings('custom_font', 'none')
            self.font_size = common.hv_settings('custom_font_size', 0)

            # Get file name
            file_name = self.view.settings().get("hex_viewer_file_name", self.view.file_name())

            # Get current bit and byte settings from view
            # Or try and get them from settings file
            # If none are found, use default
            current_bits = self.view.settings().get(
                'hex_viewer_bits',
                common.hv_settings('group_bytes_by_bits', DEFAULT_BIT_GROUP)
            )
            current_bytes = self.view.settings().get(
                'hex_viewer_bytes',
                common.hv_settings('bytes_per_line', DEFAULT_BYTES_WIDE)
            )
            # Use passed in bit and byte settings if available
            self.bits = bits if bits is not None else int(current_bits)
            self.bytes = byte_array if byte_array is not None else int(current_bytes)
            self.set_format()
        return file_name

    def is_file_too_big(self):
        """Check if file is too big and display prompt if desired."""

        file_size = float(self.thread.file_size) * 0.001
        max_file_size = float(common.hv_settings("max_file_size_kb", DEFAULT_MAX_FILE_SIZE))
        too_big = file_size > max_file_size
        if too_big and common.hv_settings("prompt_on_file_too_big", False):
            if sublime.ok_cancel_dialog(
                'File you\'re trying to open is larger than allowed (in settings). Open anyway?\n\n'
                'Skipping opening will fall back to the default action '
                '(open in external viewer if available or terminate operation).',
                'Open'
            ):
                too_big = False
        return too_big

    def read_bin(self, file_name):
        """Read the binary file."""

        global active_thread
        self.abort = False
        self.thread = ReadBin(file_name, self.bytes_wide, self.group_size, self.starting_address)
        if self.is_file_too_big():
            viewer = common.hv_settings("external_viewer", {}).get("viewer", "")
            if exists(viewer):
                self.window.run_command("hex_external_viewer")
            else:
                error(
                    "File size exceeded HexViewers configured max limit of %s KB" % str(
                        common.hv_settings("max_file_size_kb", DEFAULT_MAX_FILE_SIZE)
                    )
                )
            self.reset_thread()
        else:
            self.thread.start()
            self.handle_thread()
            active_thread = self.thread

    def load_hex_view(self):
        """Load up the hex view."""

        file_name = self.thread.file_name
        hex_name = self.thread.hex_name
        abort = self.thread.abort
        self.thread = None

        if abort:
            notify("Conversion aborted!")
            if exists(hex_name):
                remove(hex_name)
            return

        # Show binary data
        view = self.window.open_file(hex_name)

        if self.view:
            self.window.focus_view(self.view)
            if self.window.active_view().id() == self.view.id():
                self.window.run_command("close_file")
        else:
            self.window.focus_sheet(self.sheet)
            if self.window.active_sheet().id() == self.sheet.id():
                self.window.run_command("close_file")
        self.window.focus_view(view)

        # Set font
        if self.font != 'none':
            view.settings().set('font_face', self.font)
        if self.font_size != 0:
            view.settings().set("font_size", self.font_size)

        # Save hex view settings
        view.settings().set("hex_viewer_bits", self.bits)
        view.settings().set("hex_viewer_bytes", self.bytes)
        view.settings().set("hex_viewer_actual_bytes", self.bytes_wide)
        view.settings().set("hex_viewer_file_name", file_name)
        view.settings().set("hex_no_auto_open", True)
        view.settings().set("hex_viewer_fake", False)
        view.settings().set("hex_viewer_temp_file", hex_name)
        view.settings().set("hex_viewer_starting_address", self.starting_address)
        # Show hex content in view; make read only
        view.set_scratch(True)
        view.set_read_only(True)

    def read_file(self, file_name):
        """Read the file."""

        if common.hv_settings("inspector", False):
            self.window.run_command("hex_hide_inspector")
        view = self.window.open_file(file_name)
        view.settings().set("hex_no_auto_open", True)
        self.window.focus_view(self.view)
        self.window.run_command("close_file")
        self.window.focus_view(view)

    def reset_thread(self):
        """Rest the thread."""

        self.thread = None

    def handle_thread(self):
        """Handle the thread and update status."""

        if self.abort is True:
            self.thread.abort = True
            notify("Hex View aborted!")
            sublime.set_timeout(self.reset_thread, 500)
            return
        ratio = float(self.thread.read_count) / float(self.thread.file_size)
        percent = int(ratio * 10)
        leftover = 10 - percent
        message = "[" + "-" * percent + ">" + "-" * leftover + ("] %3d%%" % int(ratio * 100)) + " converted to hex"
        sublime.status_message(message)
        if not self.thread.is_alive():
            sublime.set_timeout(self.load_hex_view, 100)
        else:
            sublime.set_timeout(self.handle_thread, 100)

    def abort_hex_load(self):
        """Abort the loading of the hex view."""
        self.abort = True

    def discard_changes(self, value):
        """Discard changes."""

        if value.strip().lower() == "yes":
            if self.switch_type == "hex":
                sheet = sublime.active_window().active_sheet()
                if self.handshake == sheet.id():
                    sheet.view().set_scratch(True)
                    self.read_bin(self.file_name)
                else:
                    error("Target view is no longer in focus!  Hex view aborted.")
            else:
                self.read_file(self.file_name)
        self.reset()

    def discard_panel(self):
        """Show discard panel."""
        self.window.show_input_panel(
            "Discard Changes? (yes | no):",
            "no",
            self.discard_changes,
            None,
            self.reset
        )

    def reset(self):
        """Reset."""

        self.handshake = -1
        self.file_name = ""
        self.type = None

    def is_enabled(self, **args):
        """Check if the command is enabled."""

        view = self.window.active_view()
        return (
            (
                (
                    view is not None and
                    (
                        not args.get('reload', False) or
                        (
                            common.is_enabled() and
                            not view.settings().get("hex_viewer_fake", False)
                        )
                    ) and
                    not view.settings().get("hex_viewer_fake", False)
                ) or
                self.window.active_sheet()
            ) and
            not(active_thread is not None and active_thread.is_alive())
        )

    def run(self, bits=None, byte_array=None, starting_address=0, reload=False):
        """Run the command."""

        self.starting_address = starting_address
        if active_thread is not None and active_thread.is_alive():
            error(
                "HexViewer is already converting a file!\n"
                "Please run the abort command to stop the current conversion."
            )
            return
        # If thread is active cancel thread
        if self.thread is not None and self.thread.is_alive():
            self.abort_hex_load()
            return

        # Init Buffer
        file_name = self.buffer_init(bits, byte_array)

        # Identify view
        if self.handshake != -1 and self.handshake == self.id:
            self.reset()
        self.handshake = self.id

        if file_name is not None and exists(file_name):
            # Decide whether to read in as a binary file or a traditional file
            if self.sheet:
                self.file_name = file_name
                self.read_bin(file_name)
            elif self.view.settings().has("hex_viewer_file_name"):
                self.view_type = "hex"
                if reload:
                    self.file_name = file_name
                    common.clear_edits(self.view)
                    self.read_bin(file_name)
                elif common.is_hex_dirty(self.view):
                    self.file_name = file_name
                    if bits is None and byte_array is None:
                        self.switch_type = "file"
                    else:
                        self.switch_type = "hex"
                    self.discard_panel()
                else:
                    if bits is None and byte_array is None:
                        # Switch back to traditional output
                        self.read_file(file_name)
                    else:
                        # Reload hex with new settings
                        self.read_bin(file_name)
            elif reload:
                error("Can't reload, current file is not in hex view!")
            else:
                # We are going to swap out the current file for hex output
                # So as not to clutter the screen.  Changes need to be saved
                # Or they will be lost
                if self.view.is_dirty():
                    self.file_name = file_name
                    self.switch_type = "hex"
                    self.discard_panel()
                else:
                    # Switch to hex output
                    self.read_bin(file_name)
        else:
            if file_name is None:
                error("Hex Viewer can only edit files. Save the contents to disk first!")
            else:
                error("%s does not exist on disk!" % basename(file_name))


class HexViewerOptionsCommand(sublime_plugin.WindowCommand):
    """Set hex view options."""

    def set_bits(self, value):
        """Set group bytes by number of bits."""

        if value != -1:
            self.window.run_command('hex_viewer', {"bits": VALID_BITS[value]})

    def set_bytes(self, value):
        """Set total bytes per line."""

        if value != -1:
            self.window.run_command('hex_viewer', {"byte_array": self.valid_bytes[value]})

    def is_enabled(self):
        """Check if command is enabled."""

        view = self.window.active_view()
        return common.is_enabled() and view is not None and not view.settings().get("hex_viewer_fake", False)

    def run(self, option):
        """Run command."""

        self.view = self.window.active_view()
        file_name = self.view.settings().get("hex_viewer_file_name", self.view.file_name())
        self.valid_bytes = common.hv_settings("valid_bytes_per_line", VALID_BYTES)
        if file_name is not None:
            if self.view.settings().has("hex_viewer_file_name"):
                option_list = []
                if option == "bits":
                    for bits in VALID_BITS:
                        option_list.append(str(bits) + " bits")
                    self.window.show_quick_panel(option_list, self.set_bits)
                elif option == "bytes":
                    for byte_array in self.valid_bytes:
                        option_list.append(str(byte_array) + " bytes")
                    self.window.show_quick_panel(option_list, self.set_bytes)


class HexExternalViewerCommand(sublime_plugin.WindowCommand):
    """Open hex data in external hex program."""

    def run(self, edit):
        """Run command."""

        viewer = common.hv_settings("external_viewer", {}).get("viewer", "")
        if not exists(viewer):
            error("Can't find the external hex viewer!")
            return

        file_name = self.window.extract_variables().get('file')

        if file_name is not None and exists(file_name):
            cmd = [viewer] + common.hv_settings("external_viewer", {}).get("args", [])

            for x in range(0, len(cmd)):
                cmd[x] = cmd[x].replace("${FILE}", file_name)

            subprocess.Popen(cmd)

    def is_enabled(self):
        """Check if command is enabled."""
        file_name = self.window.extract_variables().get('file')

        viewer = common.hv_settings("external_viewer", {}).get("viewer", "")
        return exists(viewer) and file_name is not None


class HexViewerAbortCommand(sublime_plugin.WindowCommand):
    """Abort loading the hex view."""

    def run(self):
        """Run the command."""

        if active_thread is not None and active_thread.is_alive():
            active_thread.abort = True

    def is_enabled(self):
        """Check if command is enabled."""

        return active_thread is not None and active_thread.is_alive()
