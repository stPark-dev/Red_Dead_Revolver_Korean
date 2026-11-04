"""Tests for tools/fontgen.py: pack extra glyphs into new font B pages."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import fontb, fontgen

PAL4 = [(0, 0, 0, 0)] + [(0xf7, 0xf7, 0xf7, 17 * i) for i in range(1, 16)]


def desc(codes, pages):
    return {'header': b'\0' * 0x2c, 'pages': pages,
            'glyphs': [dict(code=c, x=0, y=0, w=1, h=1, yoff=-1) for c in codes]}


def solid(ch, w, h):
    from PIL import Image
    return Image.new('L', (w, h), 255)


def test_layout_fills_pages_in_order():
    d0 = desc([0x41, 0x42], [2])
    chars = [chr(0xAC00 + i) for i in range(30)]
    d1, pages = fontgen.add_pages(d0, chars, cell=(20, 30), yoff=-25, page=(64, 64), bpp=4,
                                  palette=PAL4, render=solid)
    # 64/20 = 3 per row, 64/30 = 2 rows -> 6 glyphs per page -> 5 pages
    assert len(pages) == 5
    assert d1['pages'] == [2, 8, 14, 20, 26, 32]
    new = d1['glyphs'][2:]
    assert [g['code'] for g in new] == [ord(c) for c in chars]
    assert (new[0]['x'], new[0]['y'], new[1]['x'], new[3]['y'], new[6]['x'], new[6]['y']) == (0, 0, 20, 30, 0, 0)
    assert all(g['x'] + g['w'] <= 64 and g['y'] + g['h'] <= 64 and g['yoff'] == -25 for g in new)
    assert d0['pages'] == [2] and len(d0['glyphs']) == 2  # input untouched


def test_pages_are_valid_and_drawn():
    d1, pages = fontgen.add_pages(desc([0x41], [1]), ['가'], cell=(8, 8), yoff=-8, page=(16, 16), bpp=4,
                                  palette=PAL4, render=solid)
    pg = fontb.parse_page(pages[0])
    assert (pg['w'], pg['h'], pg['bpp']) == (16, 16, 4)
    assert pg['pixels'][0] == 15 and pg['pixels'][7 * 16 + 7] == 15 and pg['pixels'][8] == 0


def test_sorts_and_rejects_duplicates_or_existing():
    with pytest.raises(ValueError):
        fontgen.add_pages(desc([0xAC00], [1]), ['가'], cell=(8, 8), yoff=-8, page=(16, 16), bpp=4,
                          palette=PAL4, render=solid)
    d1, _ = fontgen.add_pages(desc([0x41], [1]), ['나', '가', '가'], cell=(8, 8), yoff=-8, page=(16, 16),
                              bpp=4, palette=PAL4, render=solid)
    assert [g['code'] for g in d1['glyphs']] == [0x41, 0xAC00, 0xB098]


def test_rejects_cell_larger_than_page():
    with pytest.raises(ValueError):
        fontgen.add_pages(desc([0x41], [1]), ['가'], cell=(40, 8), yoff=-8, page=(32, 32), bpp=4,
                          palette=PAL4, render=solid)


def test_coverage_to_palette_index_nearest_alpha():
    m = fontgen.coverage_map(PAL4)
    assert m[0] == 0 and m[255] == 15 and m[17 * 7] == 7
