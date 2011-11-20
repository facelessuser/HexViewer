import sublime
import sublime_plugin
import re
from hex_common import *
import hashlib
import zlib

DEFAULT_CHECKSUM = "md5"
VALID_HASH = []


def verify_hashes(names):
    global VALID_HASH
    for name in names:
        if name in dir(hashlib):
            VALID_HASH.append(name)
        elif name in dir(zlib):
            VALID_HASH.append(name)
        else:
            try:
                hashlib.new(name)
                VALID_HASH.append(name)
            except ValueError:
                print "Hex Viewer: " + name + " hash is not available!"


# Extra hash SSL and ZLIB classes
class ssl_algorithm(object):
    __algorithm = None
    __name = None

    def algorithm(self, name, digest_size, arg):
        self.__algorithm = hashlib.new(name)
        self.__name = name
        self.__digest_size = digest_size
        self.update(arg)

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def copy(self):
        return None if self.__algorithm == None else self.__algorithm.copy()

    def digest(self):
        return None if self.__algorithm == None else self.__algorithm.digest()

    def hexdigest(self):
        return None if self.__algorithm == None else self.__algorithm.hexdigest()

    def update(self, arg):
        if self.__algorithm != None:
            self.__algorithm.update(arg)


class zlib_algorithm(object):
    __algorithm = None
    __name = None
    __digest_size = 0
    __hash = 0

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def algorithm(self, name, digest_size, start, arg):
        self.__algorithm = getattr(zlib, name)
        self.__name = name
        self.__digest_size
        self.__hash = start
        self.update(arg)

    def copy(self):
        return self

    def digest(self):
        return None if self.__algorithm == None else self.__hash & 0xffffffff

    def hexdigest(self):
        return None if self.__algorithm == None else '%08x' % (self.digest())

    def update(self, arg):
        if self.__algorithm != None:
            self.__hash = self.__algorithm(arg, self.__hash)


# Additional Hashes
class mdc2(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('mdc2', 16, arg)


class md4(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('md4', 16, arg)


class sha(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('sha', 20, arg)


class ripemd160(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('ripemd160', 20, arg)


class crc32(zlib_algorithm):
    def __init__(self, arg=''):
        self.algorithm('crc32', 4, 0, arg)


class adler32(zlib_algorithm):
    def __init__(self, arg=''):
        self.algorithm('adler32', 4, 1, arg)


# Sublime Text Commands
class checksum:
    def __init__(self, hash_algorithm=None, arg=""):
        if hash_algorithm == None or not hash_algorithm in VALID_HASH:
            hash_algorithm = hv_settings.get("hash_algorithm", DEFAULT_CHECKSUM)
        if not hash_algorithm in VALID_HASH:
            hash_algorithm = DEFAULT_CHECKSUM
        self.hash = getattr(hashlib, hash_algorithm)(arg)
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

    def run(self, hash_algorithm=None, panel=False):
        if not panel:
            self.get_checksum(hash_algorithm)
        else:
            self.window.show_quick_panel(VALID_HASH, self.select_checksum)

    def select_checksum(self, value):
        if value != -1:
            self.get_checksum(VALID_HASH[value])

    def get_checksum(self, hash_algorithm=None):
        view = self.window.active_view()
        if view != None:
            hex_hash = checksum(hash_algorithm)
            r_buffer = view.split_by_newlines(sublime.Region(0, view.size()))
            for line in r_buffer:
                hex_data = re.sub(r'[\da-z]{8}:[\s]{2}((?:[\da-z]+[\s]{1})*)\s*\:[\w\W]*', r'\1', view.substr(line)).replace(" ", "").decode("hex")
                hex_hash.update(hex_data)
            hex_hash.display(self.window)


# Define extra hash classes as members of hashlib
hashlib.mdc2 = mdc2
hashlib.md4 = md4
hashlib.sha = sha
hashlib.ripemd160 = ripemd160
hashlib.crc32 = crc32
hashlib.adler32 = adler32

# Compose list of hashes
verify_hashes(
    [
        'mdc2', 'md4', 'md5',
        'sha', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
        'ripemd160',
        'crc32', 'adler32'
    ]
)
