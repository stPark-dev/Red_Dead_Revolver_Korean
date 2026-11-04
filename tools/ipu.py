"""PS2 IPU still images (`*.ipu`, decoded by the IPU unit / FFmpeg's `ipu` codec).

File: 16-byte header {'ipum', u32 size = len - 8, u16 w, u16 h, u32 frames = 1}, one frame, then
00 00 01 b0 00 00 01 b1. Frame: flags byte (every game file uses 0: 8-bit DC, linear qscale,
VLC table B14, zigzag, frame DCT), then w/16 * h/16 MPEG-2 intra macroblocks with no slice
headers: '1' address increment (not before the first), type '1' (keep qscale) or '01' + 5-bit
qscale code, then 4 Y + Cb + Cr intra blocks; padding to a byte boundary.

Document model (exact round trip): mbs = [{'q': code or None, 'blocks': (6 x (dc, ((run, level[, 'e']), ...)))}],
dc is the absolute quantised DC; an 'e' marks a run/level the source wrote with the escape code.
"""
import struct
import numpy as np

MAGIC = b'ipum'
TRAILER = bytes.fromhex('000001b0000001b1')

DC_LUM = [(0x4, 3), (0x0, 2), (0x1, 2), (0x5, 3), (0x6, 3), (0xe, 4), (0x1e, 5), (0x3e, 6), (0x7e, 7),
          (0xfe, 8), (0x1fe, 9), (0x1ff, 9)]
DC_CHR = [(0x0, 2), (0x1, 2), (0x2, 2), (0x6, 3), (0xe, 4), (0x1e, 5), (0x3e, 6), (0x7e, 7), (0xfe, 8),
          (0x1fe, 9), (0x3fe, 10), (0x3ff, 10)]
_B14 = [(0x3, 2), (0x4, 4), (0x5, 5), (0x6, 7), (0x26, 8), (0x21, 8), (0xa, 10), (0x1d, 12), (0x18, 12),
        (0x13, 12), (0x10, 12), (0x1a, 13), (0x19, 13), (0x18, 13), (0x17, 13), (0x1f, 14), (0x1e, 14),
        (0x1d, 14), (0x1c, 14), (0x1b, 14), (0x1a, 14), (0x19, 14), (0x18, 14), (0x17, 14), (0x16, 14),
        (0x15, 14), (0x14, 14), (0x13, 14), (0x12, 14), (0x11, 14), (0x10, 14), (0x18, 15), (0x17, 15),
        (0x16, 15), (0x15, 15), (0x14, 15), (0x13, 15), (0x12, 15), (0x11, 15), (0x10, 15), (0x3, 3),
        (0x6, 6), (0x25, 8), (0xc, 10), (0x1b, 12), (0x16, 13), (0x15, 13), (0x1f, 15), (0x1e, 15),
        (0x1d, 15), (0x1c, 15), (0x1b, 15), (0x1a, 15), (0x19, 15), (0x13, 16), (0x12, 16), (0x11, 16),
        (0x10, 16), (0x5, 4), (0x4, 7), (0xb, 10), (0x14, 12), (0x14, 13), (0x7, 5), (0x24, 8), (0x1c, 12),
        (0x13, 13), (0x6, 5), (0xf, 10), (0x12, 12), (0x7, 6), (0x9, 10), (0x12, 13), (0x5, 6), (0x1e, 12),
        (0x14, 16), (0x4, 6), (0x15, 12), (0x7, 7), (0x11, 12), (0x5, 7), (0x11, 13), (0x27, 8), (0x10, 13),
        (0x23, 8), (0x1a, 16), (0x22, 8), (0x19, 16), (0x20, 8), (0x18, 16), (0xe, 10), (0x17, 16),
        (0xd, 10), (0x16, 16), (0x8, 10), (0x15, 16), (0x1f, 12), (0x1a, 12), (0x19, 12), (0x17, 12),
        (0x16, 12), (0x1f, 13), (0x1e, 13), (0x1d, 13), (0x1c, 13), (0x1b, 13), (0x1f, 16), (0x1e, 16),
        (0x1d, 16), (0x1c, 16), (0x1b, 16)]
_LEVEL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 1, 2, 3, 4, 5, 1, 2, 3, 4, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
_RUN = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
assert len(_B14) == len(_LEVEL) == len(_RUN) == 111
AC_CODE = {(r, l): c for r, l, c in zip(_RUN, _LEVEL, _B14)}
AC_DEC = {c: (r, l) for (r, l), c in AC_CODE.items()}
ESC, EOB = (0x1, 6), (0x2, 2)
DC_LUM_DEC = {c: s for s, c in enumerate(DC_LUM)}
DC_CHR_DEC = {c: s for s, c in enumerate(DC_CHR)}

INTRA_MATRIX = np.array([
    8, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37, 19, 22, 26, 27, 29, 34, 34, 38,
    22, 22, 26, 27, 29, 34, 37, 40, 22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58,
    26, 27, 29, 34, 38, 46, 56, 69, 27, 29, 35, 38, 46, 56, 69, 83], dtype=np.int64)
ZIGZAG = np.array([
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6,
    7, 14, 21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31,
    39, 46, 53, 60, 61, 54, 47, 55, 62, 63])


class _Reader:
    def __init__(self, b):
        self.bits = ''.join(format(x, '08b') for x in b)
        self.pos = 0

    def get(self, n):
        v = int(self.bits[self.pos:self.pos + n], 2)
        self.pos += n
        return v

    def vlc(self, table, maxlen):
        for n in range(1, maxlen + 1):
            key = (int(self.bits[self.pos:self.pos + n], 2), n)
            if key in table:
                self.pos += n
                return table[key]
        raise ValueError('bad VLC at bit %d' % self.pos)


class _Writer:
    def __init__(self):
        self.parts = []

    def put(self, v, n):
        self.parts.append(format(v, '0%db' % n))

    def bytes(self):
        s = ''.join(self.parts)
        s += '0' * (-len(s) % 8)
        return int(s, 2).to_bytes(len(s) // 8, 'big') if s else b''


AC_TABLE = dict(AC_DEC)
AC_TABLE[ESC] = 'esc'
AC_TABLE[EOB] = 'eob'


def _read_block(r, chroma, pred, comp):
    size = r.vlc(DC_CHR_DEC if chroma else DC_LUM_DEC, 10)
    diff = 0
    if size:
        v = r.get(size)
        diff = v if v >> (size - 1) else v - (1 << size) + 1
    dc = pred[comp] + diff
    pred[comp] = dc
    toks = []
    while True:
        t = r.vlc(AC_TABLE, 16)
        if t == 'eob': break
        if t == 'esc':
            run, lev = r.get(6), r.get(12)
            if lev >= 2048: lev -= 4096
            if lev in (0, -2048): raise ValueError('forbidden escape level')
            toks.append((run, lev, 'e'))
        else:
            run, lev = t
            toks.append((run, -lev if r.get(1) else lev))
    return dc, tuple(toks)


def parse(b):
    if b[:4] != MAGIC: raise ValueError('not an IPU file')
    size, w, h, frames = struct.unpack_from('<IHHI', b, 4)
    if size != len(b) - 8 or frames != 1 or w % 16 or h % 16: raise ValueError('unsupported IPU header')
    if b[-8:] != TRAILER: raise ValueError('missing IPU trailer')
    data = b[16:-8]
    flags = data[0]
    if flags: raise ValueError('unsupported IPU flags %#x' % flags)
    r = _Reader(data[1:])
    pred, mbs = [128, 128, 128], []
    for i in range((w // 16) * (h // 16)):
        if i and r.get(1) != 1: raise ValueError('bad macroblock address increment')
        if r.get(1): q = None
        elif r.get(1): q = r.get(5)
        else: raise ValueError('bad macroblock type')
        blocks = tuple(_read_block(r, n >= 4, pred, max(0, n - 3)) for n in range(6))
        mbs.append(dict(q=q, blocks=blocks))
    if (len(r.bits) - r.pos) >= 8 or int(r.bits[r.pos:] or '0', 2): raise ValueError('trailing frame data')
    return dict(w=w, h=h, flags=flags, mbs=mbs)


def _write_block(wr, blk, chroma, pred, comp):
    dc, toks = blk
    diff = dc - pred[comp]
    pred[comp] = dc
    size = abs(diff).bit_length()
    wr.put(*(DC_CHR if chroma else DC_LUM)[size])
    if size: wr.put(diff if diff > 0 else diff + (1 << size) - 1, size)
    for t in toks:
        run, lev = t[0], t[1]
        code = AC_CODE.get((run, abs(lev)))
        if code and len(t) == 2:
            wr.put(*code); wr.put(1 if lev < 0 else 0, 1)
        else:
            if not (0 <= run < 64 and -2048 < lev < 2048 and lev): raise ValueError('run/level out of range')
            wr.put(*ESC); wr.put(run, 6); wr.put(lev & 0xfff, 12)
    wr.put(*EOB)


def build(doc):
    wr = _Writer()
    wr.put(doc['flags'], 8)
    pred = [128, 128, 128]
    for i, mb in enumerate(doc['mbs']):
        if i: wr.put(1, 1)
        if mb['q'] is None: wr.put(1, 1)
        else: wr.put(1, 2); wr.put(mb['q'], 5)
        for n, blk in enumerate(mb['blocks']):
            _write_block(wr, blk, n >= 4, pred, max(0, n - 3))
    frame = wr.bytes()
    return MAGIC + struct.pack('<IHHI', 16 + len(frame), doc['w'], doc['h'], 1) + frame + TRAILER


def effective_mbs(doc):
    """[(qscale code in effect, blocks)] — what each macroblock decodes to, independent of how q is written."""
    out, q = [], None
    for mb in doc['mbs']:
        q = mb['q'] if mb['q'] is not None else q
        out.append((q, mb['blocks']))
    return out


# --- pixels -------------------------------------------------------------------------------------

def _dct_matrix():
    c = np.array([[np.sqrt((1 if k == 0 else 2) / 8) * np.cos((2 * n + 1) * k * np.pi / 16) for n in range(8)]
                  for k in range(8)])
    return c


_C = _dct_matrix()


def _dequant(blk, q):
    dc, toks = blk
    coef = np.zeros(64, np.int64)
    coef[0] = dc * 8
    pos = 0
    for t in toks:
        pos += t[0] + 1
        if pos > 63: raise ValueError('coefficient index overflow')
        lev = t[1]
        v = abs(lev) * int(INTRA_MATRIX[ZIGZAG[pos]]) * 2 * q * 2 // 32
        coef[ZIGZAG[pos]] = max(-2048, min(2047, -v if lev < 0 else v))
    if coef.sum() % 2 == 0: coef[63] ^= 1  # mismatch control
    return coef.reshape(8, 8)


def _idct(coef):
    return _C.T @ coef @ _C


def decode_yuv(doc):
    w, h = doc['w'], doc['h']
    Y = np.zeros((h, w)); Cb = np.zeros((h // 2, w // 2)); Cr = np.zeros((h // 2, w // 2))
    for i, (q, blocks) in enumerate(effective_mbs(doc)):
        y, x = (i // (w // 16)) * 16, (i % (w // 16)) * 16
        px = [_idct(_dequant(b, q)) for b in blocks]
        Y[y:y + 8, x:x + 8], Y[y:y + 8, x + 8:x + 16] = px[0], px[1]
        Y[y + 8:y + 16, x:x + 8], Y[y + 8:y + 16, x + 8:x + 16] = px[2], px[3]
        Cb[y // 2:y // 2 + 8, x // 2:x // 2 + 8] = px[4]
        Cr[y // 2:y // 2 + 8, x // 2:x // 2 + 8] = px[5]
    return tuple(np.clip(np.round(p), 0, 255).astype(np.uint8) for p in (Y, Cb, Cr))


def yuv_to_rgb(Y, Cb, Cr):
    """BT.601 limited range, chroma upsampled by repetition."""
    y = (Y.astype(float) - 16) * 255 / 219
    cb = (np.repeat(np.repeat(Cb, 2, 0), 2, 1).astype(float) - 128) * 255 / 224
    cr = (np.repeat(np.repeat(Cr, 2, 0), 2, 1).astype(float) - 128) * 255 / 224
    rgb = np.stack([y + 1.402 * cr, y - 0.344136 * cb - 0.714136 * cr, y + 1.772 * cb], -1)
    return np.clip(np.round(rgb), 0, 255).astype(np.uint8)


def rgb_to_yuv(rgb):
    f = rgb.astype(float)
    y = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    cb = (f[..., 2] - y) / 1.772
    cr = (f[..., 0] - y) / 1.402
    Y = 16 + y * 219 / 255
    sub = lambda c: (c[0::2, 0::2] + c[1::2, 0::2] + c[0::2, 1::2] + c[1::2, 1::2]) / 4
    return Y, 128 + sub(cb) * 224 / 255, 128 + sub(cr) * 224 / 255


def decode(doc):
    return yuv_to_rgb(*decode_yuv(doc))


def _encode_block(px, q):
    coef = _C @ px @ _C.T
    dc = int(np.clip(np.round(coef[0, 0] / 8), 0, 255))
    flat = coef.reshape(64)
    toks, run = [], 0
    for pos in range(1, 64):
        k = ZIGZAG[pos]
        lev = int(np.round(16 * flat[k] / (INTRA_MATRIX[k] * 2 * q)))
        lev = max(-2047, min(2047, lev))
        if lev == 0:
            run += 1
        else:
            toks.append((run, lev)); run = 0
    return dc, tuple(toks)


def _encode_mb(Y, Cb, Cr, mx, my, q):
    y, x = my * 16, mx * 16
    ys = [Y[y:y + 8, x:x + 8], Y[y:y + 8, x + 8:x + 16], Y[y + 8:y + 16, x:x + 8], Y[y + 8:y + 16, x + 8:x + 16]]
    cs = [Cb[y // 2:y // 2 + 8, x // 2:x // 2 + 8], Cr[y // 2:y // 2 + 8, x // 2:x // 2 + 8]]
    return tuple(_encode_block(b, q) for b in ys + cs)


def encode(rgb, q=2):
    h, w = rgb.shape[:2]
    if w % 16 or h % 16: raise ValueError('image size must be a multiple of 16')
    if not 1 <= q <= 31: raise ValueError('q out of range')
    Y, Cb, Cr = rgb_to_yuv(rgb)
    mbs = [dict(q=q if i == 0 else None, blocks=_encode_mb(Y, Cb, Cr, i % (w // 16), i // (w // 16), q))
           for i in range((w // 16) * (h // 16))]
    return build(dict(w=w, h=h, flags=0, mbs=mbs))


def replace_region(doc, rgb, rect, q=2):
    """New doc with every macroblock touching rect (x0, y0, x1, y1; exclusive end) re-encoded from rgb
    (full-frame image). Other macroblocks keep their coefficients; q codes are rewritten only where
    needed so every untouched macroblock still decodes with its original qscale."""
    w, h = doc['w'], doc['h']
    if rgb.shape[:2] != (h, w): raise ValueError('image size differs from the IPU frame')
    x0, y0, x1, y1 = rect
    Y, Cb, Cr = rgb_to_yuv(rgb)
    eff = effective_mbs(doc)
    out, cur = [], None
    for i, (oq, blocks) in enumerate(eff):
        mx, my = i % (w // 16), i // (w // 16)
        orig = doc['mbs'][i]
        if mx * 16 < x1 and (mx + 1) * 16 > x0 and my * 16 < y1 and (my + 1) * 16 > y0:
            mb, eq = dict(q=None if q == cur else q, blocks=_encode_mb(Y, Cb, Cr, mx, my, q)), q
        elif orig['q'] is not None or cur == oq:
            mb, eq = dict(orig), oq
        else:
            mb, eq = dict(q=oq, blocks=blocks), oq
        out.append(mb)
        cur = eq
    return dict(doc, mbs=out)
