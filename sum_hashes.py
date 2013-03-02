"""
Hex Viewer
Licensed under MIT
Copyright (c) 2013 Isaac Muse <isaacmuse@gmail.com>
"""

BIT8_MOD = 256
BIT16_MOD = 65536
BIT24_MOD = 16777216
BIT32_MOD = 4294967296


class sum8(object):
    __name = "sum8"
    __digest_size = 1

    def __init__(self, arg=""):
        self.sum = 0
        self.update(arg)

    @property
    def name(self):
        return self.__name

    @property
    def digest_size(self):
        return self.__digest_size

    def update(self, arg):
        for b in arg:
            self.sum += ord(b)

    def digest(self):
        return self.sum % BIT8_MOD

    def hexdigest(self):
        return "%02x" % self.digest()

    def copy(self):
        import copy
        return copy.deepcopy(self)


class sum16(sum8):
    __name = "sum16"
    __digest_size = 2

    def digest(self):
        return self.sum % BIT16_MOD

    def hexdigest(self):
        return "%04x" % self.digest()


class sum24(sum8):
    __name = "sum24"
    __digest_size = 3

    def digest(self):
        return self.sum % BIT24_MOD

    def hexdigest(self):
        return "%06x" % self.digest()


class sum32(sum8):
    __name = "sum32"
    __digest_size = 4

    def digest(self):
        return self.sum % BIT32_MOD

    def hexdigest(self):
        return "%08x" % self.digest()


class xor8(sum8):
    __name = "xor8"
    __digest_size = 1

    def update(self, arg):
        for b in arg:
            self.sum ^= ord(b) & 0xFF

    def digest(self):
        return int(self.sum)

    def hexdigest(self):
        return "%02x" % self.digest()
