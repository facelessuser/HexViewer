"""
Hex Viewer
Licensed under MIT
Copyright (c) 2011-2015 Isaac Muse <isaacmuse@gmail.com>
"""

import sublime
import sublime_plugin
from os.path import dirname, exists
from HexViewer.hex_common import *
from HexViewer.hex_checksum import checksum, parse_view_data
import threading
import traceback
from io import StringIO
from HexViewer.hex_notify import notify, error

USE_CHECKSUM_ON_SAVE = True
WRITE_GOOD = 0
WRITE_FAIL = 1

active_thread = None


class ThreadedWrite(threading.Thread):
    def __init__(self, data, file_name, fmt_callback=None, count=None):
        self.data = data
        self.file_name = file_name
        self.chunk = 0
        self.chunks = len(data) if count is None else count
        self.abort = False
        self.fmt_callback = fmt_callback if fmt_callback is not None else self.format
        self.status = WRITE_GOOD
        threading.Thread.__init__(self)

    def format(self, data):
        for x in data:
            yield x

    def run(self):
        try:
            with open(self.file_name, "wb") as f:
                for chunk in self.fmt_callback(self.data):
                    self.chunk += 1
                    if self.abort:
                        return
                    else:
                        f.write(chunk)
        except:
            self.status = WRITE_FAIL
            print(str(traceback.format_exc()))


class HexWriterAbortCommand(sublime_plugin.WindowCommand):
    def run(self):
        global active_thread
        if active_thread is not None and active_thread.is_alive():
            active_thread.abort = True

    def is_enabled(self):
        global active_thread
        return active_thread is not None and active_thread.is_alive()


class HexWriterCommand(sublime_plugin.WindowCommand):
    export_path = ""
    handshake = -1

    def is_enabled(self):
        global active_thread
        view = self.window.active_view()
        return (
            is_enabled() and
            view is not None and not view.settings().get("hex_viewer_fake", False) and
            not (active_thread is not None and active_thread.is_alive())
        )

    def export_panel(self):
        self.window.show_input_panel(
            "Export To:",
            self.export_path,
            self.prepare_export,
            None,
            self.reset
        )

    def overwrite(self, value):
        if value.strip().lower() == "yes":
            self.export()
        else:
            self.export_path = self.view.settings().get("hex_viewer_file_name")
            self.export_panel()

    def prepare_export(self, file_path):
        self.export_path = file_path
        if exists(dirname(file_path)):
            if exists(file_path):
                self.window.show_input_panel(
                    "Overwrite File? (yes | no):",
                    "no",
                    self.overwrite,
                    None,
                    self.reset
                )
            else:
                self.export()
        else:
            error("Directory does not exist!")
            self.export_path = self.view.settings().get("hex_viewer_file_name")
            self.export_panel()

    def reset_thread(self):
        self.thread = None

    def finish_export(self):
        if hv_settings("checksum_on_save", USE_CHECKSUM_ON_SAVE):
            hex_hash = checksum()
            self.hex_buffer.seek(0)
            # Checksum will be threaded and will show the result when done
            sublime.set_timeout(lambda: sublime.status_message("Checksumming..."), 0)
            hex_hash.threaded_update(self.hex_buffer, parse_view_data, self.row)

        # Update the tab name
        self.view.set_name(basename(self.export_path) + ".hex")
        # Update the internal path
        self.view.settings().set("hex_viewer_file_name", self.export_path)
        # Tie it to a real view if not already
        self.view.settings().set("hex_viewer_fake", False)
        # Clear the marked edits
        clear_edits(self.view)
        # Reset class
        self.reset()

    def export_thread(self):
        ratio = float(self.thread.chunk) / float(self.thread.chunks)
        percent = int(ratio * 10)
        leftover = 10 - percent
        message = "[" + "-" * percent + ">" + "-" * leftover + ("] %3d%%" % int(ratio * 100)) + " chunks written"
        sublime.status_message(message)
        if not self.thread.is_alive():
            if self.thread.abort is True:
                notify("Write aborted!")
                sublime.set_timeout(lambda: self.reset_thread(), 500)
            else:
                status = self.thread.status
                self.reset_thread()
                if status == WRITE_GOOD:
                    sublime.set_timeout(lambda: self.finish_export(), 500)
                else:
                    error("Failed to export to " + self.export_path)
        else:
            sublime.set_timeout(lambda: self.export_thread(), 500)

    def export(self):
        global active_thread
        self.view = self.window.active_view()
        if self.handshake != -1 and self.handshake == self.view.id():
            try:
                sublime.set_timeout(lambda: sublime.status_message("Writing..."), 0)
                self.row = self.view.rowcol(self.view.size())[0] - 1
                self.hex_buffer = StringIO(self.view.substr(sublime.Region(0, self.view.size())))
                self.thread = ThreadedWrite(self.hex_buffer, self.export_path, parse_view_data, self.row)
                self.thread.start()
                self.export_thread()
                active_thread = self.thread
            except:
                print(str(traceback.format_exc()))
                error("Failed to export to " + self.export_path)
                self.reset()
                return

        else:
            error("Hex view is no longer in focus! File not saved.")
            self.reset()

    def reset(self):
        self.export_path = ""
        self.handshake = -1
        self.reset_thread()

    def run(self):
        global active_thread
        if active_thread is not None and active_thread.is_alive():
            error("HexViewer is already exporting a file!\nPlease run the abort command to stop the current export.")
        else:
            self.view = self.window.active_view()

            # Identify view
            if self.handshake != -1 and self.handshake == self.view.id():
                self.reset()
            self.handshake = self.view.id()

            self.export_path = self.view.settings().get("hex_viewer_file_name")

            self.export_panel()
