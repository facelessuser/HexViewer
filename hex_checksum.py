'''
Hex Viewer
Licensed under MIT
Copyright (c) 2011 Isaac Muse <isaacmuse@gmail.com>
'''

import sublime
import sublime_plugin
import re
from hex_common import *
import threading
import hashlib
import zlib
import sys

# Try and include additional hashes
try:
    import whirlpool
except:
    class whirlpool(object):
        whirlpool = None

try:
    import tiger
except:
    class tiger(object):
        tiger = None

DEFAULT_CHECKSUM = "md5"
VALID_HASH = []

active_thread = None


def verify_hashes(hashes):
    global VALID_HASH
    for item in hashes:
        module = item.split(":")
        if len(module) == 2:
            try:
                getattr(sys.modules[module[0]], module[1])
                VALID_HASH.append(module[1])
            except:
                print "Hex Viewer: " + module[1] + " hash is not available!"
        else:
            try:
                hashlib.new(item)
                VALID_HASH.append(item)
            except:
                print "Hex Viewer: " + item + " hash is not available!"


# Extra hash SSL and ZLIB classes
class ssl_algorithm(object):
    __algorithm = None
    __name = None

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def algorithm(self, name, digest_size, arg):
        self.__algorithm = hashlib.new(name)
        self.__name = name
        self.__digest_size = digest_size
        self.update(arg)

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
class md2(ssl_algorithm):
    def __init__(self, arg=''):
        self.algorithm('md2', 16, arg)


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
class checksum(object):
    thread = None

    def __init__(self, hash_algorithm=None, data=""):
        if hash_algorithm == None or not hash_algorithm in VALID_HASH:
            hash_algorithm = hv_settings.get("hash_algorithm", DEFAULT_CHECKSUM)
        if not hash_algorithm in VALID_HASH:
            hash_algorithm = DEFAULT_CHECKSUM
        self.hash = getattr(hashlib, hash_algorithm)(data)
        self.name = hash_algorithm

    def update(self, data=""):
        if isinstance(data, basestring):
            self.hash.update(data)

    def threaded_update(self, data=[]):
        if not isinstance(data, basestring):
            global active_thread
            self.thread = hash_thread(data, self.hash)
            self.thread.start()
            self.chunk_thread()
            active_thread = self

    def chunk_thread(self):
        ratio = float(self.thread.chunk) / float(self.thread.chunks)
        percent = int(ratio * 10)
        leftover = 10 - percent
        message = "[" + "-" * percent + ">" + "-" * leftover + ("] %3d%%" % int(ratio * 100)) + " chunks hashed"
        sublime.status_message(message)
        if not self.thread.is_alive():
            if self.thread.abort == True:
                sublime.status_message("Hash calculation aborted!")
                sublime.set_timeout(lambda: self.reset_thread(), 500)
            else:
                sublime.set_timeout(lambda: self.display(), 500)
        else:
            sublime.set_timeout(lambda: self.chunk_thread(), 500)

    def reset_thread(self):
        self.thread = None

    def display(self, window=None):
        if window == None:
            window = sublime.active_window()
        window.show_input_panel(self.name + ":", str(self.hash.hexdigest()), None, None, None)


class hash_thread(threading.Thread):
    def __init__(self, data, obj):
        self.hash = False
        self.data = data
        self.obj = obj
        self.chunk = 0
        self.chunks = len(data)
        self.abort = False
        threading.Thread.__init__(self)

    def run(self):
        for chunk in self.data:
            self.chunk += 1
            if self.abort:
                return
            else:
                self.obj.update(chunk)


class HashSelectionCommand(sublime_plugin.WindowCommand):
    algorithm = "md5"

    def has_selections(self):
        single = False
        view = self.window.active_view()
        if view != None:
            if len(view.sel()) > 0:
                single = True
        return single

    def hash_eval(self, value):
        if value != -1:
            self.algorithm = VALID_HASH[value]
            if self.has_selections():
                # Initialize hasher and related values
                data = []
                view = self.window.active_view()
                hasher = checksum(self.algorithm)
                # Walk through all selections breaking up data by lines
                for sel in view.sel():
                    lines = view.substr(sel).splitlines(True)
                    for line in lines:
                        data.append(''.join(unichr(ord(c)).encode('utf-8') for c in line))
                hasher.threaded_update(data)

    def run(self):
        if self.has_selections():
            self.window.show_quick_panel(VALID_HASH, self.hash_eval)


class HashEvalCommand(sublime_plugin.WindowCommand):
    algorithm = "md5"

    def hash_eval(self, value):
        data = []
        hasher = checksum(self.algorithm)
        lines = value.splitlines(True)
        for line in lines:
            data.append(''.join(unichr(ord(c)).encode('utf-8') for c in line))
        hasher.threaded_update(data)

    def select_hash(self, value):
        if value != -1:
            self.algorithm = VALID_HASH[value]
            self.window.show_input_panel(
                "hash input:",
                "",
                self.hash_eval,
                None,
                None
            )

    def run(self, hash_algorithm=None):
        self.window.show_quick_panel(VALID_HASH, self.select_hash)


class HexChecksumCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return is_enabled()

    def run(self, hash_algorithm=None, panel=False):
        global active_thread
        if active_thread != None and active_thread.thread != None and active_thread.thread.is_alive():
            active_thread.thread.abort = True
        else:
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
            sublime.set_timeout(lambda: sublime.status_message("Checksumming..."), 0)
            hex_hash = checksum(hash_algorithm)
            r_buffer = view.split_by_newlines(sublime.Region(0, view.size()))
            hex_data = []
            for line in r_buffer:
                hex_data.append(re.sub(r'[\da-z]{8}:[\s]{2}((?:[\da-z]+[\s]{1})*)\s*\:[\w\W]*', r'\1', view.substr(line)).replace(" ", "").decode("hex"))
            hex_hash.threaded_update(hex_data)


# Compose list of hashes
verify_hashes(
    [
        'md2', 'mdc2', 'md4', 'md5',
        'sha', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
        'ripemd160',
        'zlib:crc32', 'zlib:adler32',
        'whirlpool:whirlpool',
        'tiger:tiger'
    ]
)

#Define extra hash classes as members of hashlib
hashlib.md2 = md2
hashlib.mdc2 = mdc2
hashlib.md4 = md4
hashlib.sha = sha
hashlib.ripemd160 = ripemd160
hashlib.crc32 = crc32
hashlib.adler32 = adler32
hashlib.whirlpool = whirlpool.whirlpool
hashlib.tiger = tiger.tiger
