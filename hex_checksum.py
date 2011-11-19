import sublime
import sublime_plugin
import re
from hex_common import *
import hashlib
import zlib

VALID_HASH = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512", "adler32", "crc32"]
DEFAULT_CHECKSUM = VALID_HASH[0]


# Additional Hashes
class crc32(object):
    name = 'crc32'
    digest_size = 4

    def __init__(self, arg=''):
        self.__hash = 0
        self.update(arg)

    def copy(self):
        return self

    def digest(self):
        return self.__hash & 0xffffffff

    def hexdigest(self):
        return '%08x' % (self.digest())

    def update(self, arg):
        self.__hash = zlib.crc32(arg, self.__hash)


class adler32(object):
    name = 'adler32'
    digest_size = 4

    def __init__(self, arg=''):
        self.__hash = 1
        self.update(arg)

    def copy(self):
        return self

    def digest(self):
        return self.__hash & 0xffffffff

    def hexdigest(self):
        return '%08x' % (self.digest())

    def update(self, arg):
        self.__hash = zlib.adler32(arg, self.__hash)


hashlib.crc32 = crc32
hashlib.adler32 = adler32


class checksum:
    def __init__(self, hash_algorithm=None):
        if hash_algorithm == None or not hash_algorithm in VALID_HASH:
            hash_algorithm = hv_settings.get("hash_algorithm", DEFAULT_CHECKSUM)
        if not hash_algorithm in VALID_HASH:
            hash_algorithm = DEFAULT_CHECKSUM
        self.hash = getattr(hashlib, hash_algorithm)()
        self.name = hash_algorithm

    def update(self, hex_data):
        self.hash.update(hex_data)

    def display(self, window):
        window.show_input_panel(self.name + ":", str(self.hash.hexdigest()), None, None, None)


class HexChecksumEvalCommand(sublime_plugin.WindowCommand):
    def run(self, data, hash_algorithm=None):
        checksum(hash_algorithm).update(data.decode("hex")).display(self.window)


class HexChecksumCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled()

    def run(self, hash_algorithm=None):
        view = self.window.active_view()
        if view != None:
            hex_hash = checksum(hash_algorithm)
            r_buffer = view.split_by_newlines(sublime.Region(0, view.size()))
            for line in r_buffer:
                hex_data = re.sub(r'[\da-z]{8}:[\s]{2}((?:[\da-z]+[\s]{1})*)\s*\:[\w\W]*', r'\1', view.substr(line)).replace(" ", "").decode("hex")
                hex_hash.update(hex_data)
            hex_hash.display(self.window)
