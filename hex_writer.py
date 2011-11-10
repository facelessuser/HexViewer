import sublime
import sublime_plugin
from os.path import dirname, exists
import re
from hex_common import *


class HexWriterCommand(sublime_plugin.WindowCommand):
    export_path = ""
    handshake = -1

    def is_enabled(self):
        return is_enabled()

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
            sublime.error_message("Directory does not exist!")
            self.export_path = self.view.settings().get("hex_viewer_file_name")
            self.export_panel()

    def export(self):
        self.view = self.window.active_view()
        if self.handshake != -1 and self.handshake == self.view.id():
            try:
                with open(self.export_path, "wb") as bin:
                    r_buffer = self.view.split_by_newlines(sublime.Region(0, self.view.size()))
                    for line in r_buffer:
                        data = re.sub(r'[\da-z]{8}:[\s]{2}((?:[\da-z]+[\s]{1})*)\s*\:[\w\W]*', r'\1', self.view.substr(line)).strip().replace(" ", "")
                        bin.write(data.decode("hex"))
                self.view.settings().set("hex_viewer_file_name", self.export_path)
                clear_edits(self.view)
            except:
                sublime.error_message("Faild to export to " + self.export_path)
            self.reset()
        else:
            sublime.error_message("Hex view is no longer in focus! File not saved.")
            self.reset()

    def reset(self):
        self.export_path = ""
        self.handshake = -1

    def run(self):
        self.view = self.window.active_view()

        # Identify view
        if self.handshake != -1 and self.handshake == self.view.id():
            self.reset()
        self.handshake = self.view.id()

        self.export_path = self.view.settings().get("hex_viewer_file_name")

        self.export_panel()
