"""Tests for tools/gfxtext.py: Korean redraw of text baked into IPU images (spec text/gfx_ko.json)."""
import os, sys, hashlib
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import ipu, gfxtext

FONT = os.path.join(ROOT, '..', 'fonts', 'NotoSerifKR-Black.otf')
pytestmark = pytest.mark.skipif(not os.path.exists(FONT), reason='Korean font missing')


def paper_with_text():
    rgb = np.full((64, 96, 3), 190, np.uint8)
    rgb[20:28, 20:60] = 30  # "English text" block
    rgb[50:60, 70:90] = (120, 20, 20)  # red decoration that must survive
    return ipu.encode(rgb, q=1)


def spec_for(src, **over):
    item = dict(en='WORD', box=[16, 16, 64, 32], mask='dark', lines=['가나'], x=20, align='l', y=17, size=12,
                color='ink', font='title')
    item.update(over)
    return dict(src_sha1=hashlib.sha1(src).hexdigest(), q=1, items=[item])


COLORS = {'ink': [28, 22, 18], 'red': [88, 14, 14]}
FONTS = {'title': FONT}


def test_apply_erases_box_draws_korean_and_keeps_rest():
    src = paper_with_text()
    out = gfxtext.apply(src, spec_for(src), FONTS, COLORS)
    a, b = ipu.decode(ipu.parse(src)), ipu.decode(ipu.parse(out))
    assert np.array_equal(a[48:, :], b[48:, :])  # macroblocks away from the box: pixel identical
    assert (b[16:32, 16:64].mean(-1) < 100).sum() > 10  # Korean strokes drawn
    assert (b[20:28, 50:60].mean(-1) < 100).sum() < 5  # old text gone where no Korean is drawn


def test_apply_is_deterministic():
    src = paper_with_text()
    assert gfxtext.apply(src, spec_for(src), FONTS, COLORS) == gfxtext.apply(src, spec_for(src), FONTS, COLORS)


def test_apply_rejects_other_source():
    src = paper_with_text()
    spec = spec_for(src); spec['src_sha1'] = '0' * 40
    with pytest.raises(ValueError, match='source'):
        gfxtext.apply(src, spec, FONTS, COLORS)


def test_text_must_fit_its_box():
    src = paper_with_text()
    with pytest.raises(ValueError, match='outside'):
        gfxtext.apply(src, spec_for(src, lines=['가나다라마바사아자차']), FONTS, COLORS)


@pytest.mark.parametrize('bad', [dict(align='x'), dict(lines=[]), dict(color='blue'), dict(mask='odd'), dict(font='serif'),
                                 dict(box=[10, 10, 5, 20])])
def test_invalid_items_rejected(bad):
    src = paper_with_text()
    with pytest.raises(ValueError):
        gfxtext.apply(src, spec_for(src, **bad), FONTS, COLORS)


def test_dark_gray_mask_spares_red_pixels():
    rgb = np.full((32, 32, 3), 190, np.uint8)
    rgb[4:8, 4:28] = 30
    rgb[20:24, 4:28] = (110, 20, 20)
    m = gfxtext.text_mask(rgb, [0, 0, 32, 32], 'dark_gray')
    assert m[5, 10] and not m[21, 10]
    assert gfxtext.text_mask(rgb, [0, 0, 32, 32], 'dark')[21, 10]


def test_all_mask_covers_whole_box():
    rgb = np.zeros((16, 16, 3), np.uint8)
    assert gfxtext.text_mask(rgb, [2, 3, 10, 12], 'all').sum() == 8 * 9


def test_pitch_sets_line_spacing():
    src = paper_with_text()
    a = spec_for(src, box=[0, 0, 96, 64], lines=['가', '가'], y=2)
    b = spec_for(src, box=[0, 0, 96, 64], lines=['가', '가'], y=2, pitch=30)
    _, la, _ = gfxtext._layout(a['items'][0], FONT)
    _, lb, _ = gfxtext._layout(b['items'][0], FONT)
    assert la[1][2] - la[0][2] == 12 + gfxtext.LINE_GAP and lb[1][2] - lb[0][2] == 30
