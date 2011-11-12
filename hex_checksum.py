import sublime
import sublime_plugin
import re
from hex_common import *
import hashlib

VALID_HASH = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
DEFAULT_CHECKSUM = VALID_HASH[0]


class HexChecksumEvalCommand(sublime_plugin.WindowCommand):
    def run(self, data, hash_algorithm=DEFAULT_CHECKSUM):
        if not hash_algorithm in VALID_HASH:
            hash_algorithm = DEFAULT_CHECKSUM
        h = getattr(hashlib, hash_algorithm)
        self.window.show_input_panel(hash_algorithm + ":", str(h(data).hexdigest()), None, None, None)


class HexChecksumCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled()

    def run(self, hash_algorithm=None):
        view = self.window.active_view()
        if view != None:
            if hash_algorithm != None and not hash_algorithm in VALID_HASH:
                hash_algorithm = hv_settings.get("checksom_algorithm", DEFAULT_CHECKSUM)
            r_buffer = view.split_by_newlines(sublime.Region(0, view.size()))
            hex_data = ''
            for line in r_buffer:
                data = re.sub(r'[\da-z]{8}:[\s]{2}((?:[\da-z]+[\s]{1})*)\s*\:[\w\W]*', r'\1', view.substr(line)).replace(" ", "")
                hex_data += data.decode("hex")
            self.window.run_command("hex_checksum_eval", {"hash_algorithm": hash_algorithm, "data": hex_data})
