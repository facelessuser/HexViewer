"""
Hex Viewer.

Licensed under MIT
Copyright (c) 2011-2015 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime
import sublime_plugin
import re
import HexViewer.hex_common as common
import threading
import hashlib
import zlib
import sys
from HexViewer import whirlpool, tiger, sum_hashes
from binascii import unhexlify
from io import StringIO
import traceback
from HexViewer.hex_notify import notify, error

DEFAULT_CHECKSUM = "md5"
VALID_HASH = []
SUPPORT_EXTRA = []

active_thread = None


def parse_view_data(data_buffer):
    """Parse the hex data."""

    for line in data_buffer:
        yield unhexlify(
            re.sub(r'[\da-fA-F]{8}:[\s]{2}((?:[\da-fA-F]+[\s]{1})*)\s*\:[\w\W]*', r'\1', line).replace(" ", "")
        )


def verify_hashes(hashes):
    """Verify the hashes are valid."""

    for item in hashes:
        module = item.split(":")
        if len(module) == 2:
            try:
                getattr(sys.modules[module[0]], module[1])
                VALID_HASH.append(module[1])
            except Exception:
                SUPPORT_EXTRA.append("Hex Viewer: " + module[1] + " hash is not available!")
        else:
            try:
                hashlib.new(item)
                VALID_HASH.append(item)
            except Exception:
                SUPPORT_EXTRA.append("Hex Viewer: " + item + " hash is not available!")


# Extra hash SSL and ZLIB classes
class SSlAlgorithm(object):
    """SSL hash algorithm."""

    __algorithm = None
    __name = None

    @property
    def name(self):
        """The name of the hash."""

        return self.__name

    @property
    def digest_size(self):
        """Size fo the digest."""

        return self.__digest_size

    def algorithm(self, name, digest_size, arg):
        """The main algorithm."""
        self.__algorithm = hashlib.new(name)
        self.__name = name
        self.__digest_size = digest_size
        self.update(arg)

    def copy(self):
        """Get copy."""

        return None if self.__algorithm is None else self.__algorithm.copy()

    def digest(self):
        """Get digest."""

        return None if self.__algorithm is None else self.__algorithm.digest()

    def hexdigest(self):
        """Get hex digest."""

        return None if self.__algorithm is None else self.__algorithm.hexdigest()

    def update(self, arg):
        """Update the hash."""

        if self.__algorithm is not None:
            self.__algorithm.update(arg)


class ZlibAlgorithm(object):
    """Zlib hash algorithm."""

    __algorithm = None
    __name = None
    __digest_size = 0
    __hash = 0

    @property
    def name(self):
        """The hash name."""

        return self.__name

    @property
    def digest_size(self):
        """Size of the digest."""

        return self.__digest_size

    def algorithm(self, name, digest_size, start, arg):
        """The main algorithm."""

        self.__algorithm = getattr(zlib, name)
        self.__name = name
        self.__digest_size = digest_size
        self.__hash = start
        self.update(arg)

    def copy(self):
        """Get copy."""

        import copy
        return copy.deepcopy(self)

    def digest(self):
        """Get digest."""

        return None if self.__algorithm is None else self.__hash & 0xffffffff

    def hexdigest(self):
        """Get hex digest."""

        return None if self.__algorithm is None else '%08x' % (self.digest())

    def update(self, arg):
        """Update the hash."""

        if self.__algorithm is not None:
            self.__hash = self.__algorithm(arg, self.__hash)


# Additional Hashes
class md2(SSlAlgorithm):  # noqa

    """md2 hash."""

    def __init__(self, arg=b''):
        """Initialize."""

        self.algorithm('md2', 16, arg)


class mdc2(SSlAlgorithm):  # noqa

    """mdc2 hash."""

    def __init__(self, arg=b''):
        """Initialize."""

        self.algorithm('mdc2', 16, arg)


class md4(SSlAlgorithm):  # noqa

    """md4 hash."""

    def __init__(self, arg=b''):
        """Initialize."""

        self.algorithm('md4', 16, arg)


class sha(SSlAlgorithm):  # noqa

    """sha hash."""

    def __init__(self, arg=b''):
        """Initialize."""

        self.algorithm('sha', 20, arg)


class ripemd160(SSlAlgorithm):  # noqa

    """ripemd160 hash."""

    def __init__(self, arg=b''):
        """Initialize."""

        self.algorithm('ripemd160', 20, arg)


class crc32(ZlibAlgorithm):  # noqa

    """crc32 hash."""

    def __init__(self, arg=b''):
        """Initialize."""

        self.algorithm('crc32', 4, 0, arg)


class adler32(ZlibAlgorithm):  # noqa

    """adler32 hash."""

    def __init__(self, arg=b''):
        """Initialize."""

        self.algorithm('adler32', 4, 1, arg)


# Sublime Text Commands
class Checksum(object):
    """Checksum."""

    thread = None

    def __init__(self, hash_algorithm=None, data=b""):
        """Initialize."""

        if hash_algorithm is None or hash_algorithm not in VALID_HASH:
            hash_algorithm = common.hv_settings("hash_algorithm", DEFAULT_CHECKSUM)
        if hash_algorithm not in VALID_HASH:
            hash_algorithm = DEFAULT_CHECKSUM
        self.hash = getattr(hashlib, hash_algorithm)(data)
        self.name = hash_algorithm

    def update(self, data=""):
        """Update hash with data."""

        if isinstance(data, str):
            self.hash.update(data)

    def threaded_update(self, data_buffer=None, fmt_callback=None, count=None):
        """Hash the data via a thread."""
        global active_thread
        if data_buffer is None:
            data_buffer = []
        self.thread = HashThread(data_buffer, self.hash, fmt_callback, count)
        self.thread.start()
        self.chunk_thread()
        active_thread = self.thread

    def chunk_thread(self):
        """Check how many chunks have been processed and update status."""

        ratio = float(self.thread.chunk) / float(self.thread.chunks)
        percent = int(ratio * 10)
        leftover = 10 - percent
        message = "[" + "-" * percent + ">" + "-" * leftover + ("] %3d%%" % int(ratio * 100)) + " chunks hashed"
        sublime.status_message(message)
        if not self.thread.is_alive():
            if self.thread.abort is True:
                notify("Hash calculation aborted!")
                sublime.set_timeout(self.reset_thread, 500)
            else:
                sublime.set_timeout(self.display, 500)
        else:
            sublime.set_timeout(self.chunk_thread, 500)

    def reset_thread(self):
        """Reset."""

        self.thread = None

    def display(self, window=None):
        """Display hash."""

        if window is None:
            window = sublime.active_window()
        if common.use_hex_lowercase():
            digest = str(self.hash.hexdigest())
        else:
            digest = str(self.hash.hexdigest()).upper()
        window.show_input_panel(self.name + ":", digest, None, None, None)


class HashThread(threading.Thread):
    """Thread hashing."""

    def __init__(self, data, obj, fmt_callback=None, count=None):
        """Initialize."""

        self.hash = False
        self.data = data
        self.obj = obj
        self.chunk = 0
        self.chunks = len(data) if count is None else count
        self.abort = False
        self.fmt_callback = fmt_callback if fmt_callback is not None else self.format
        threading.Thread.__init__(self)

    def format(self, data):
        """Format."""

        for x in data:
            yield x

    def run(self):
        """Run command."""

        try:
            for chunk in self.fmt_callback(self.data):
                self.chunk += 1
                if self.abort:
                    return
                else:
                    self.obj.update(chunk)
        except Exception:
            print(str(traceback.format_exc()))


class HashSelectionCommand(sublime_plugin.WindowCommand):
    """Hash view selections."""

    algorithm = "md5"

    def has_selections(self):
        """Check if the view has selections."""
        single = False
        view = self.window.active_view()
        if view is not None:
            if len(view.sel()) > 0:
                single = True
        return single

    def hash_eval(self, value):
        """Evaluate selection with selected hash."""

        if value != -1:
            self.algorithm = VALID_HASH[value]
            if self.has_selections():
                # Initialize hasher and related values
                data = []
                view = self.window.active_view()
                hasher = Checksum(self.algorithm)
                # Walk through all selections breaking up data by lines
                for sel in view.sel():
                    lines = view.substr(sel).splitlines(True)
                    for line in lines:
                        data.append(line.encode("utf-8"))
                hasher.threaded_update(data)

    def run(self):
        """Run command."""

        if self.has_selections():
            self.window.show_quick_panel(VALID_HASH, self.hash_eval)


class HashEvalCommand(sublime_plugin.WindowCommand):
    """Evaluate hash."""

    algorithm = "md5"

    def hash_eval(self, value):
        """Hash the value."""

        data = []
        hasher = Checksum(self.algorithm)
        lines = value.splitlines(True)
        for line in lines:
            data.append(line.encode("utf-8"))
        hasher.threaded_update(data)

    def select_hash(self, value):
        """Select the hash."""

        if value != -1:
            self.algorithm = VALID_HASH[value]
            self.window.show_input_panel(
                "hash input:",
                "",
                self.hash_eval,
                None,
                None
            )

    def run(self):
        """Run command."""

        self.window.show_quick_panel(VALID_HASH, self.select_hash)


class HexChecksumCommand(sublime_plugin.WindowCommand):
    """Checksum command."""

    def is_enabled(self):
        """Check if command is enabled."""

        return (
            common.is_enabled() and
            not (active_thread is not None and active_thread.is_alive())
        )

    def run(self, hash_algorithm=None, panel=False):
        """Run command."""

        if active_thread is not None and active_thread.is_alive():
            error(
                "HexViewer is already checksumming a file!\n"
                "Please run the abort command to stop the current checksum."
            )
        else:
            if not panel:
                self.get_checksum(hash_algorithm)
            else:
                self.window.show_quick_panel(VALID_HASH, self.select_checksum)

    def select_checksum(self, value):
        """Select the the checksum."""

        if value != -1:
            self.get_checksum(VALID_HASH[value])

    def get_checksum(self, hash_algorithm=None):
        """Get the user desired checksum."""

        view = self.window.active_view()
        if view is not None:
            sublime.set_timeout(lambda: sublime.status_message("Checksumming..."), 0)
            hex_hash = Checksum(hash_algorithm)
            row = view.rowcol(view.size())[0] - 1
            hex_hash.threaded_update(
                StringIO(view.substr(sublime.Region(0, view.size()))),
                parse_view_data,
                row
            )


class HexChecksumAbortCommand(sublime_plugin.WindowCommand):
    """Abort checksum command."""

    def run(self):
        """Run command."""

        if active_thread is not None and active_thread.is_alive():
            active_thread.abort = True

    def is_enabled(self):
        """Check if command should be enabled."""

        return active_thread is not None and active_thread.is_alive()


# Compose list of hashes
verify_hashes(
    [
        'md2', 'mdc2', 'md4', 'md5',
        'sha', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
        'ripemd160',
        'zlib:crc32', 'zlib:adler32',
        'HexViewer.whirlpool:whirlpool',
        'HexViewer.tiger:tiger',
        "HexViewer.sum_hashes:sum8",
        "HexViewer.sum_hashes:sum16",
        "HexViewer.sum_hashes:sum32",
        "HexViewer.sum_hashes:sum24",
        "HexViewer.sum_hashes:xor8"
    ]
)

# Define extra hash classes as members of hashlib
hashlib.md2 = md2
hashlib.mdc2 = mdc2
hashlib.md4 = md4
hashlib.sha = sha
hashlib.ripemd160 = ripemd160
hashlib.crc32 = crc32
hashlib.adler32 = adler32
hashlib.whirlpool = whirlpool.whirlpool
hashlib.tiger = tiger.tiger
hashlib.sum8 = sum_hashes.sum8
hashlib.sum16 = sum_hashes.sum16
hashlib.sum24 = sum_hashes.sum24
hashlib.sum32 = sum_hashes.sum32
hashlib.xor8 = sum_hashes.xor8
