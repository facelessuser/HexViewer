"""
Hex Viewer.

Licensed under MIT
Copyright (c) 2013-2015 Isaac Muse <isaacmuse@gmail.com>
"""

BIT8_MOD = 256
BIT16_MOD = 65536
BIT24_MOD = 16777216
BIT32_MOD = 4294967296


class sum8(object):

    """Sum8 hash."""

    __name = "sum8"
    __digest_size = 1

    def __init__(self, arg=b""):
        """Initialize."""

        self.sum = 0
        self.update(arg)

    @property
    def name(self):
        """Name of the hash."""

        return self.__name

    @property
    def digest_size(self):
        """Size of the digest."""

        return self.__digest_size

    def update(self, arg):
        """Update the hash."""

        for b in arg:
            self.sum += int(b)

    def digest(self):
        """Get the digest."""

        return self.sum % BIT8_MOD

    def hexdigest(self):
        """Get the hex digest."""

        return "%02x" % self.digest()

    def copy(self):
        """Get the copy."""
        import copy
        return copy.deepcopy(self)


class sum16(sum8):

    """Sum16 hash."""

    __name = "sum16"
    __digest_size = 2

    def digest(self):
        """Get the digest."""

        return self.sum % BIT16_MOD

    def hexdigest(self):
        """Get the hex digest."""

        return "%04x" % self.digest()


class sum24(sum8):

    """Sum24 hash."""

    __name = "sum24"
    __digest_size = 3

    def digest(self):
        """Get the digest."""
        return self.sum % BIT24_MOD

    def hexdigest(self):
        """Get the hex digest."""
        return "%06x" % self.digest()


class sum32(sum8):

    """Sum32 hash."""

    __name = "sum32"
    __digest_size = 4

    def digest(self):
        """Get the digest."""

        return self.sum % BIT32_MOD

    def hexdigest(self):
        """Get the hex digest."""

        return "%08x" % self.digest()


class xor8(sum8):

    """Xor8 hash."""

    __name = "xor8"
    __digest_size = 1

    def update(self, arg):
        """Update the hash."""

        for b in arg:
            self.sum ^= int(b) & 0xFF

    def digest(self):
        """Get the digest."""

        return int(self.sum)

    def hexdigest(self):
        """Get the hex digest."""

        return "%02x" % self.digest()
