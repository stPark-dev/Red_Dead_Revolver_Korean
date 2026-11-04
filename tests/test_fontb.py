"""Tests for tools/fontb.py (HUD/2D font: descriptor + 8bpp texture pages)."""
import glob, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import fontb

DESC = os.path.join(ROOT, 'work/x/FRONT/0004.bin')
PAGE = os.path.join(ROOT, 'work/x/FRONT/0005.bin')
need = pytest.mark.skipif(not os.path.exists(DESC), reason='extracted FRONT.DAT not present')


@need
def test_parse_front_0004():
    f = fontb.parse(open(DESC, 'rb').read())
    assert len(f['glyphs']) == 179
    assert f['pages'] == [45, 87, 115, 158, 177, 179]
    g = f['glyphs'][0]
    assert (g['code'], g['x'], g['y'], g['w'], g['h'], g['yoff']) == (0x21, 0, 0, 5, 0x15, -19)
    codes = [g['code'] for g in f['glyphs']]
    assert codes == sorted(codes) and codes[-1] == 0x2122


@need
def test_descriptor_roundtrip_all_copies():
    n = 0
    for p in glob.glob(os.path.join(ROOT, 'work/x/*/*.bin')):
        b = open(p, 'rb').read()
        if b[:4] != fontb.MAGIC: continue
        assert fontb.build(fontb.parse(b)) == b, p
        n += 1
    assert n > 60


@need
def test_page_roundtrip():
    b = open(PAGE, 'rb').read()
    pg = fontb.parse_page(b)
    assert (pg['w'], pg['h']) == (128, 128)
    assert len(pg['pixels']) == 128 * 128 and len(pg['palette']) == 256
    assert fontb.build_page(pg) == b


def test_add_glyph_keeps_sorted_and_page_bounds():
    f = {'header': b'\0' * 0x2c,
         'glyphs': [dict(code=0x41, x=0, y=0, w=4, h=4, yoff=-4),
                    dict(code=0x2122, x=4, y=0, w=4, h=4, yoff=-4)],
         'pages': [1, 2]}
    g = fontb.add_glyph(f, dict(code=0xAC00, x=8, y=0, w=4, h=4, yoff=-4))
    assert [x['code'] for x in g['glyphs']] == [0x41, 0x2122, 0xAC00]
    assert g['pages'] == [1, 3]
    assert len(f['glyphs']) == 2  # source untouched


def test_add_glyph_rejects_out_of_order():
    f = {'header': b'\0' * 0x2c, 'glyphs': [dict(code=0xAC01, x=0, y=0, w=1, h=1, yoff=0)], 'pages': [1]}
    with pytest.raises(ValueError):
        fontb.add_glyph(f, dict(code=0xAC00, x=0, y=0, w=1, h=1, yoff=0))




def _pages_of_size(size):
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'work/x/FRONT/*.bin'))):
        b = open(p, 'rb').read()
        if len(b) == size and b[:4] == bytes.fromhex('80008000'): out.append(b)
    return out


@need
def test_page_4bpp_roundtrip_and_unpacked_pixels():
    pages = _pages_of_size(14 + 64 + 128 * 64)
    assert pages
    for b in pages:
        pg = fontb.parse_page(b)
        assert pg['bpp'] == 4 and len(pg['palette']) == 16
        assert len(pg['pixels']) == 128 * 128 and max(pg['pixels']) < 16
        assert fontb.build_page(pg) == b


@need
def test_page_8bpp_reports_bpp():
    assert fontb.parse_page(open(PAGE, 'rb').read())['bpp'] == 8


def test_blank_page_4bpp_shape():
    pal = [(0, 0, 0, 0)] + [(0xf7, 0xf7, 0xf7, 17 * i) for i in range(1, 16)]
    pg = fontb.blank_page(256, 256, 4, pal)
    b = fontb.build_page(pg)
    assert len(b) == 14 + 64 + 256 * 128
    assert b[:6] == bytes.fromhex('000100011000')
    assert fontb.parse_page(b)['pixels'] == bytearray(256 * 256)


def test_build_rejects_more_than_24_pages():
    # the loader copies page bounds into a 24-slot array at font+0x188 (header fields follow at +0x1e8)
    f = {'header': b'\0' * 0x2c, 'glyphs': [dict(code=i, x=0, y=0, w=1, h=1, yoff=0) for i in range(25)],
         'pages': list(range(1, 26))}
    with pytest.raises(ValueError):
        fontb.build(f)
    fontb.build(dict(f, pages=list(range(2, 26))))
