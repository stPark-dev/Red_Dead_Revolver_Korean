"""Tests for tools/build_patch.py planning logic (glyph coverage, unmapped characters, budget)."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_patch as bp

CODES = {'berrylium': set(map(ord, 'ABCabc!.½')), 'damaged': set(map(ord, 'XYZ'))}
SRC = {'t/a': dict(font='berrylium', src='Abc!'), 't/b': dict(font='berrylium', src='Wait…'),
       't/c': dict(font='damaged', src='XY')}


def test_plan_collects_new_hangul_per_font():
    sel = {'t/a': '가나 다!', 't/b': 'Wait…', 't/c': '라X'}
    plan = bp.glyph_plan(SRC, sel, CODES)
    assert plan == {'berrylium': ['가', '나', '다'], 'damaged': ['라']}


def test_plan_allows_glyphless_chars_only_where_source_had_them():
    assert bp.glyph_plan(SRC, {'t/b': 'Wait…'}, CODES) == {'berrylium': [], 'damaged': []}
    with pytest.raises(bp.Unmapped) as ex:
        bp.glyph_plan(SRC, {'t/a': 'Abc…'}, CODES)
    assert 'U+2026' in str(ex.value) and 't/a' in str(ex.value)


def test_plan_rejects_non_hangul_missing_glyph():
    with pytest.raises(bp.Unmapped):
        bp.glyph_plan(SRC, {'t/a': 'A~'}, CODES)


def test_whitespace_needs_no_glyph():
    assert bp.glyph_plan(SRC, {'t/a': 'A b\nc　'.replace('　', ' ')}, CODES)['berrylium'] == []


def test_page_count_and_budget():
    assert bp.pages_needed(0, (22, 22), 256) == 0
    assert bp.pages_needed(121, (22, 22), 256) == 1
    assert bp.pages_needed(122, (22, 22), 256) == 2
    with pytest.raises(ValueError):
        bp.check_budget({'berrylium': 30, 'damaged': 0}, {'berrylium': 6, 'damaged': 6}, page_bytes=32846,
                        budget=10 ** 7)
    with pytest.raises(ValueError):
        bp.check_budget({'berrylium': 10, 'damaged': 10}, {'berrylium': 6, 'damaged': 6}, page_bytes=32846,
                        budget=600_000)
    assert bp.check_budget({'berrylium': 10, 'damaged': 2}, {'berrylium': 6, 'damaged': 6}, page_bytes=32846,
                           budget=600_000) == 12 * 32846


def test_plan_uses_every_rendering_font():
    src = dict(SRC, **{'t/d': dict(font='berrylium', fonts=['berrylium', 'damaged'], src='Title')})
    plan = bp.glyph_plan(src, {'t/d': '제목'}, CODES)
    assert plan == {'berrylium': ['목', '제'], 'damaged': ['목', '제']}


def test_plan_rejects_layout_font_without_glyph_support():
    src = dict(SRC, **{'t/d': dict(font='berrylium', fonts=['steelfish'], src='Chapter 1')})
    with pytest.raises(bp.Unmapped):
        bp.glyph_plan(src, {'t/d': '제1장'}, CODES)


def test_choose_page_smallest_that_fits_one_page():
    assert bp.choose_page(2, (22, 26)) == 64
    assert bp.choose_page(4, (22, 26)) == 64
    assert bp.choose_page(10, (22, 26)) == 128
    assert bp.choose_page(500, (22, 26)) == 256
    assert bp.choose_page(0, (22, 26)) == 256


def test_every_font_config_fits_a_page():
    for f, (cell, yoff, ttf) in bp.FONTS.items():
        assert cell[0] <= 256 and cell[1] <= 256 and yoff < 0, f


def _pup(text):
    return b'\xff\xfe' + text.encode('utf-16-le')


def test_pupshow_patch_replaces_cues_by_key():
    orig = _pup('00:01.0\t"Hi, you."\t\t5\r\n\r\n00:02.0\tBye.\tNow.\t5\r\n')
    out = bp.pupshow_patch(orig, {'1': '잘 가.\n지금.'})
    assert out.decode('utf-16') == '00:01.0\t"Hi, you."\t\t5\r\n\r\n00:02.0\t잘 가.\t지금.\t5\r\n'
    assert bp.pupshow_patch(orig, {'0': 'Hi, you.', '1': 'Bye.\nNow.'}) == orig  # source text keeps bytes


def test_subtitle_width_limit_is_widest_reachable_source_line():
    widths = {ord('A'): 10, ord('B'): 20}
    recs = [dict(src='AA\nB', reach='game'), dict(src='BBB', reach='game'), dict(src='BBBBBB', reach='swat-only')]
    assert bp.subtitle_width_limit(recs, widths) == 60


def test_code_literals_merge_into_layout_literals():
    refs = {'key_fonts': {'Back': {'fonts': ['berrylium']}}, 'literals': {'Enter': {'fonts': ['berrylium']}}}
    code = {'literals': {'Player 1 Paused': {'fonts': ['regulatorcondensed'], 'evidence': 'ELF "Player %d Paused"'}}}
    out = bp.merge_code_literals(refs, code)
    assert out['literals']['Player 1 Paused'] == {'fonts': ['regulatorcondensed']}
    assert 'Player 1 Paused' not in refs['literals']  # input untouched


@pytest.mark.parametrize('lit', ['Enter', 'Back'])
def test_code_literal_may_not_shadow_layout_literal_or_key(lit):
    refs = {'key_fonts': {'Back': {'fonts': ['berrylium']}}, 'literals': {'Enter': {'fonts': ['berrylium']}}}
    with pytest.raises(ValueError):
        bp.merge_code_literals(refs, {'literals': {lit: {'fonts': ['berrylium'], 'evidence': 'x'}}})


def test_code_literal_needs_evidence_and_fonts():
    refs = {'key_fonts': {}, 'literals': {}}
    with pytest.raises(ValueError):
        bp.merge_code_literals(refs, {'literals': {'Player 1': {'fonts': ['berrylium']}}})
    with pytest.raises(ValueError):
        bp.merge_code_literals(refs, {'literals': {'Player 1': {'fonts': [], 'evidence': 'x'}}})


# --- graphics text (IPU images) ---------------------------------------------------------------
import hashlib
import numpy as np
import ipu

GFX_FONT = os.path.join(ROOT, '..', 'fonts', 'NotoSerifKR-Black.otf')
need_font = pytest.mark.skipif(not os.path.exists(GFX_FONT), reason='Korean font missing')


def gfx_spec(src, state='needs_review', aliases=()):
    return dict(fonts={'title': GFX_FONT}, colors={'ink': [28, 22, 18]}, images={'a.ipu': dict(
        aliases=list(aliases), state=state, src_sha1=hashlib.sha1(src).hexdigest(), q=1,
        items=[dict(en='X', box=[0, 0, 32, 16], mask='dark', lines=['가'], x=2, align='l', y=1, size=12,
                    color='ink', font='title')])})


def small_ipu():
    return ipu.encode(np.full((32, 32, 3), 190, np.uint8), q=1)


@need_font
def test_gfx_plan_renders_image_and_aliases():
    src = small_ipu()
    out = bp.gfx_plan(gfx_spec(src, aliases=['b.ipu']), {'a.ipu': [src, src], 'b.ipu': [src]}, 'dev')
    assert set(out) == {'a.ipu', 'b.ipu'} and out['a.ipu'] == out['b.ipu'] != src


@need_font
def test_gfx_plan_rejects_copy_that_differs_from_spec():
    src = small_ipu()
    with pytest.raises(ValueError, match='a.ipu'):
        bp.gfx_plan(gfx_spec(src), {'a.ipu': [src, src + b'x']}, 'dev')


@need_font
def test_gfx_plan_rejects_missing_image():
    with pytest.raises(ValueError, match='not found'):
        bp.gfx_plan(gfx_spec(small_ipu(), aliases=['b.ipu']), {'a.ipu': [small_ipu()]}, 'dev')


@need_font
def test_gfx_plan_release_needs_eligible_state():
    src = small_ipu()
    with pytest.raises(SystemExit):
        bp.gfx_plan(gfx_spec(src), {'a.ipu': [src]}, 'release')
    assert bp.gfx_plan(gfx_spec(src, state='distribution_eligible'), {'a.ipu': [src]}, 'release')


# --- swui button recentering ------------------------------------------------------------------
MENU = ('<FONT:berrylium:SCALE:0.750,0.750>\r\n'
        '<BUTTON:23,-20,0:Player:CALLB:0,0:640,448:0:-1:multioption_profile>\r\n'
        '<BUTTON:12,0,0:Controls:CALLB:0,0:640,448:0:-1:multioption_controls>\r\n')
RULE = dict(font='berrylium', scale=0.75, center_x=48, labels=['Player', 'Controls'])


def test_text_width_uses_glyph_widths_and_space():
    assert bp.text_width('가 나', {ord('가'): 22, ord('나'): 20}, 14) == 56


def test_text_width_adds_tracking_per_glyph():
    assert bp.text_width('가 나', {ord('가'): 22, ord('나'): 20}, 14, tracking=1) == 58


def test_font_metrics_reads_tracking_and_space():
    hdr = bytes.fromhex('5c8f823f') + (29).to_bytes(4, 'little') + (1).to_bytes(4, 'little') + (14).to_bytes(4, 'little')
    assert bp.font_metrics(hdr + bytes(28)) == (1, 14)


def test_swui_recenter_handles_combo_labels():
    text = '<COMBO:18,68,0:Vibration:6,84:86,12:10>\r\n'
    out = bp.swui_recenter(text, dict(RULE, labels=['Vibration']), {'Vibration': '진동'}, {ord(c): 22 for c in '진동'}, 14)
    assert out == text.replace('<COMBO:18,', '<COMBO:32,')


def test_text_width_rejects_missing_glyph():
    with pytest.raises(bp.Unmapped):
        bp.text_width('가', {}, 14)


def test_swui_recenter_moves_only_button_x():
    out = bp.swui_recenter(MENU, RULE, {'Player': '플레이어', 'Controls': '조작'}, {ord(c): 22 for c in '플레이어조작'}, 14)
    assert out == MENU.replace('<BUTTON:23,', '<BUTTON:15,').replace('<BUTTON:12,', '<BUTTON:32,')


def test_swui_recenter_needs_each_label_once():
    with pytest.raises(ValueError, match='Missing'):
        bp.swui_recenter(MENU, dict(RULE, labels=['Missing']), {'Missing': '가'}, {ord('가'): 22}, 14)


def test_swui_recenter_group_keeps_gaps_and_group_centre():
    text = '<BUTTON:350,163,0:no:CALLB:0>\r\n<BUTTON:250,163,0:yes:CALLB:0>\r\n'
    widths = {ord(c): 10 for c in 'NoYes'}
    widths.update({ord(c): 20 for c in '예아니요'})
    rule = dict(font='f', scale=1.5, mode='group', labels=['no', 'yes'])
    out = bp.swui_recenter(text, rule, {'no': '아니요', 'yes': '예'}, widths, 14, english={'no': 'No', 'yes': 'Yes'})
    # English: yes 250..295, no 350..380 -> centre 315, gap 55. Korean 30 + 55 + 90 = 175 -> starts 227.5
    assert out == text.replace('BUTTON:350,', 'BUTTON:313,').replace('BUTTON:250,', 'BUTTON:228,')


def test_gfx_plan_beta_rejects_unfinished_image():
    src = small_ipu()
    with pytest.raises(SystemExit, match='not ready for beta'):
        bp.gfx_plan(gfx_spec(src, state='in_progress'), {'a.ipu': [src]}, 'beta')


def test_require_clean_rejects_uncommitted_inputs_for_public_builds():
    bp.require_clean('dev', ' M text/strtbl_ko.jsonl\n')            # dev builds may use a dirty tree
    bp.require_clean('beta', '?? work/x.png\n M README.md\n')        # only build inputs matter
    for policy in ('beta', 'release'):
        with pytest.raises(SystemExit, match='text/strtbl_ko.jsonl'):
            bp.require_clean(policy, ' M text/strtbl_ko.jsonl\n')
        with pytest.raises(SystemExit, match='tools/new.py'):
            bp.require_clean(policy, '?? tools/new.py\n')
