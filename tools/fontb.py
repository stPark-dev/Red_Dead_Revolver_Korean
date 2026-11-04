"""HUD/2D font ("font B") used by the UTF-16 text renderer at 0x17A078.

Descriptor (e.g. FRONT/0004): 0x2C-byte header (starts with f32 1.02), u32 glyphCount,
glyphCount x 10-byte records {u32 code, u8 x, u8 y, u8 w, u8 h, s16 yoff} sorted by code,
u32 pageCount, u32 pageEnd[pageCount] (exclusive glyph index bound of each page).
Codes < 0x100 go through a byte table; larger codes are binary-searched, so any UTF-16
code can be added as long as the list stays sorted.

Texture page (the archive entries following the descriptor): 14-byte header
{u16 w, u16 h, ...}, 256 x RGBA palette, w*h linear 8-bit indices.
"""
import struct

MAGIC = bytes.fromhex('5c8f823f')
HDR = 0x2C
REC = struct.Struct('<IBBBBh')
PAGE_HDR = 14


def parse(b):
    if b[:4] != MAGIC: raise ValueError('not a font B descriptor')
    n = struct.unpack_from('<I', b, HDR)[0]
    o = HDR + 4
    glyphs = []
    for _ in range(n):
        code, x, y, w, h, yoff = REC.unpack_from(b, o); o += REC.size
        glyphs.append(dict(code=code, x=x, y=y, w=w, h=h, yoff=yoff))
    np_ = struct.unpack_from('<I', b, o)[0]; o += 4
    pages = list(struct.unpack_from('<%dI' % np_, b, o)); o += 4 * np_
    if o != len(b): raise ValueError('trailing bytes in descriptor')
    return dict(header=bytes(b[:HDR]), glyphs=glyphs, pages=pages)


MAX_PAGES = 24  # loader copies page bounds into font+0x188; header fields start at +0x1e8


def build(f):
    if len(f['pages']) > MAX_PAGES:
        raise ValueError('%d pages exceed the loader limit of %d' % (len(f['pages']), MAX_PAGES))
    out = bytearray(f['header'])
    out += struct.pack('<I', len(f['glyphs']))
    for g in f['glyphs']:
        out += REC.pack(g['code'], g['x'], g['y'], g['w'], g['h'], g['yoff'])
    out += struct.pack('<I', len(f['pages'])) + struct.pack('<%dI' % len(f['pages']), *f['pages'])
    return bytes(out)


def add_glyph(f, g, new_page=False):
    """Return a new descriptor with glyph g appended to the last page (or a new page)."""
    if f['glyphs'] and g['code'] <= f['glyphs'][-1]['code']:
        raise ValueError('glyph code %#x breaks sort order' % g['code'])
    glyphs = f['glyphs'] + [dict(g)]
    pages = f['pages'][:] + [len(glyphs)] if new_page else f['pages'][:-1] + [len(glyphs)]
    return dict(header=f['header'], glyphs=glyphs, pages=pages)


FMT = {8: 0x0e, 4: 0x10}  # texture format code at page header +4
PAGE_TAIL = bytes.fromhex('0100000001000100')


def parse_page(b):
    """Font page: 14-byte header {u16 w, u16 h, u16 fmt, ...}, RGBA palette, linear pixels.

    8bpp: 256 colours, one byte per pixel. 4bpp: 16 colours, two pixels per byte, low nibble first.
    'pixels' is always one palette index per pixel.
    """
    w, h, fmt = struct.unpack_from('<HHH', b, 0)
    bpp = {v: k for k, v in FMT.items()}.get(fmt)
    if bpp is None: raise ValueError('unknown page format %#x' % fmt)
    ncol = 1 << bpp
    if len(b) != PAGE_HDR + 4 * ncol + w * h * bpp // 8: raise ValueError('unexpected page size')
    pal = [tuple(b[PAGE_HDR + 4 * i: PAGE_HDR + 4 * i + 4]) for i in range(ncol)]
    raw = b[PAGE_HDR + 4 * ncol:]
    if bpp == 8:
        pixels = bytearray(raw)
    else:
        pixels = bytearray(w * h)
        pixels[0::2] = bytes(x & 15 for x in raw)
        pixels[1::2] = bytes(x >> 4 for x in raw)
    return dict(header=bytes(b[:PAGE_HDR]), w=w, h=h, bpp=bpp, palette=pal, pixels=pixels)


def build_page(pg):
    px = pg['pixels']
    if pg['bpp'] == 4:
        px = bytes(a | (c << 4) for a, c in zip(px[0::2], px[1::2]))
    return pg['header'] + b''.join(bytes(c) for c in pg['palette']) + bytes(px)


def blank_page(w, h, bpp, palette):
    if len(palette) != 1 << bpp: raise ValueError('palette size does not match bpp')
    header = struct.pack('<HHH', w, h, FMT[bpp]) + PAGE_TAIL
    return dict(header=header, w=w, h=h, bpp=bpp, palette=[tuple(c) for c in palette],
                pixels=bytearray(w * h))
