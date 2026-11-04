"""Packed entry names of lowercase 'Dave' archives (Angel engine, RDR PS2).

Each name is a little-endian bit stream of 6-bit codes ending with code 0, padded to a byte.
A name may start with a prefix-copy pair (c0 >= 56, c1 >= 32): copy (c0 - 56) + (c1 - 32) * 8
characters from the previous entry's name. Names are stored back to front: entry 0 has the
highest offset in the name table.
"""
import struct

CHARS = {1: ' ', 4: '(', 5: ')', 6: '-', 7: '.', 20: '_', 48: '~'}
CHARS.update({10 + i: str(i) for i in range(10)})
CHARS.update({21 + i: chr(ord('a') + i) for i in range(26)})
CODES = {v: k for k, v in CHARS.items()}
MAX_PREFIX = 7 + 31 * 8


def _codes(b):
    v = int.from_bytes(b, 'little')
    i = 0
    while True:
        c = (v >> (6 * i)) & 63
        yield c
        i += 1


def decode(b, prev=''):
    it = _codes(b)
    c = next(it)
    out = ''
    if c >= 56:
        c1 = next(it)
        out = prev[:(c - 56) + (c1 - 32) * 8]
        c = next(it)
    while c:
        if c not in CHARS: raise ValueError('unknown name code %d' % c)
        out += CHARS[c]
        c = next(it)
    return out


def encode_one(name, prev=''):
    n = 0
    while n < min(len(name), len(prev), MAX_PREFIX) and name[n] == prev[n]: n += 1
    codes = []
    if n:
        codes += [56 + n % 8, 32 + n // 8]
    codes += [CODES[ch] for ch in name[n:]] + [0]
    v = sum(c << (6 * i) for i, c in enumerate(codes))
    return v.to_bytes((6 * len(codes) + 7) // 8, 'little')


def encode(names):
    """Return (blob, offsets) with entry 0 last in the blob, offsets relative to the blob start."""
    parts = [encode_one(n, names[i - 1] if i else '') for i, n in enumerate(names)]
    blob = b''.join(reversed(parts))
    offs, o = [0] * len(parts), len(blob)
    for i, p in enumerate(parts):
        o -= len(p); offs[i] = o
    return blob, offs


def decode_all(blob, offs):
    names, prev = [], ''
    for o in offs:
        prev = decode(blob[o:o + 64], prev)
        names.append(prev)
    return names


def names_of(d):
    n, ts, ns = struct.unpack_from('<III', d, 4)
    nb = 0x800 + ts
    offs = [struct.unpack_from('<I', d, 0x800 + 16 * i)[0] for i in range(n)]
    return decode_all(bytes(d[nb:nb + ns]) + b'\0' * 64, offs)
