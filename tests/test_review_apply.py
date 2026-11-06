"""Tests for tools/review_export.py (subtitle/layout/graphics rows) and tools/review_apply.py (sheet -> translation files)."""
import os, sys, copy
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import review_export as rx
import review_apply as ra

PUP_SRC = {'pupshow/a_en.txt/%d' % i: dict(id='pupshow/a_en.txt/%d' % i, table='a_en.txt', key=str(i), font='berrylium',
                                            src='Line %d\nmore' % i) for i in (0, 1, 2, 10)}
PUP_RECS = [dict(id=k, src=v['src'], ko='줄 %s\n더' % v['key'], state='needs_review') for k, v in sorted(PUP_SRC.items())]
LAYOUT = {'_doc': 'x', 'table': 'swat.strtbl', 'entries': {'Back': dict(ko='뒤로', state='needs_review'),
                                                          'Accept': dict(ko='확인', state='distribution_eligible')}}
GFX = {'_doc': 'x', 'images': {'gameover.ipu': dict(state='needs_review', items=[
    dict(en='GAME OVER', lines=['게임 오버'], box=[0, 0, 9, 9]),
    dict(en='TRY AGAIN', lines=['다시', '하기'], box=[0, 0, 9, 9])])}}


def test_pup_rows_follow_cue_order_in_one_table():
    rows = rx.pup_rows(PUP_SRC, PUP_RECS)
    assert [r['id'] for r in rows] == ['pupshow/a_en.txt/0', 'pupshow/a_en.txt/1', 'pupshow/a_en.txt/2', 'pupshow/a_en.txt/10']
    assert {r['table'] for r in rows} == {'pupshow'}
    assert rows[0]['en'] == 'Line 0\\nmore' and rows[0]['ko'] == '줄 0\\n더'


def test_layout_and_gfx_rows():
    assert rx.layout_rows(LAYOUT) == [dict(id='layout/Accept', table='layout', en='Accept', ko='확인'),
                                      dict(id='layout/Back', table='layout', en='Back', ko='뒤로')]
    assert rx.gfx_rows(GFX) == [dict(id='gfx/gameover.ipu/0', table='gfx', en='GAME OVER', ko='게임 오버'),
                                dict(id='gfx/gameover.ipu/1', table='gfx', en='TRY AGAIN', ko='다시\\n하기')]


def test_from_tsv_rows_keeps_english_for_checks():
    text = rx.to_tsv(rx.layout_rows(LAYOUT))
    assert rx.from_tsv_rows(text) == [('layout/Accept', 'Accept', '확인'), ('layout/Back', 'Back', '뒤로')]


def test_apply_layout_changes_only_edited_rows():
    lt, n, errs = ra.apply_layout(LAYOUT, {'Accept': '확인', 'Back': '돌아가기'})
    assert (n, errs) == (1, [])
    assert lt['entries']['Back'] == dict(ko='돌아가기', state='needs_review')
    assert lt['entries']['Accept']['state'] == 'distribution_eligible'   # unchanged row keeps its state
    assert LAYOUT['entries']['Back']['ko'] == '뒤로'                      # input not mutated


def test_apply_layout_rejects_unknown_and_missing_glyph():
    _, _, errs = ra.apply_layout(LAYOUT, {'Nope': '없음', 'Back': '뒤로…'})
    assert any('Nope' in e for e in errs) and any('U+2026' in e for e in errs)


def test_apply_gfx_sets_lines_and_image_state():
    g = copy.deepcopy(GFX); g['images']['gameover.ipu']['state'] = 'distribution_eligible'
    out, n, errs = ra.apply_gfx(g, {'gameover.ipu/1': '다시\n해라', 'gameover.ipu/0': '게임 오버'})
    assert (n, errs) == (1, [])
    img = out['images']['gameover.ipu']
    assert img['items'][1]['lines'] == ['다시', '해라'] and img['state'] == 'needs_review'
    assert g['images']['gameover.ipu']['items'][1]['lines'] == ['다시', '하기']


def test_apply_gfx_rejects_unknown_item():
    _, _, errs = ra.apply_gfx(GFX, {'gameover.ipu/5': 'x', 'nothere.ipu/0': 'y'})
    assert len(errs) == 2


def test_apply_jsonl_merges_changed_rows_only():
    recs = [dict(r) for r in PUP_RECS]; recs[0]['state'] = 'distribution_eligible'
    new = {'pupshow/a_en.txt/0': '줄 0\n더', 'pupshow/a_en.txt/1': '바뀐 줄\n더'}
    out, n, errs = ra.apply_jsonl(PUP_SRC, recs, new)
    by = {r['id']: r for r in out}
    assert (n, errs) == (1, [])
    assert by['pupshow/a_en.txt/1']['ko'] == '바뀐 줄\n더' and by['pupshow/a_en.txt/1']['state'] == 'needs_review'
    assert by['pupshow/a_en.txt/0']['state'] == 'distribution_eligible'


def test_apply_jsonl_reports_token_errors():
    src = {'t/a': dict(id='t/a', table='t', key='a', font='f', src='Press {BTN_BD}')}
    _, _, errs = ra.apply_jsonl(src, [dict(id='t/a', src='Press {BTN_BD}', ko='{BTN_BD} 누르기', state='needs_review')],
                                {'t/a': '누르기'})
    assert errs and 'token' in errs[0]


def test_route_splits_by_id_prefix():
    rows = [('pupshow/a_en.txt/0', 'x', '가'), ('layout/Back', 'Back', '나'), ('gfx/gameover.ipu/0', 'GAME OVER', '다'),
            ('swat.strtbl/k', 'y', '라')]
    assert ra.route(rows) == {'pupshow': {'pupshow/a_en.txt/0': '가'}, 'layout': {'Back': '나'},
                              'gfx': {'gameover.ipu/0': '다'}, 'strtbl': {'swat.strtbl/k': '라'}}


def test_english_mismatch_catches_shifted_rows():
    en = {'layout/Back': 'Back', 'layout/Accept': 'Accept'}
    rows = [('layout/Back', 'Accept', '확인'), ('layout/Accept', 'Accept', '확인')]
    errs = ra.english_mismatch(rows, en)
    assert len(errs) == 1 and 'layout/Back' in errs[0]


def test_english_mismatch_ignores_tsv_whitespace_escaping():
    # to_tsv turns tabs into spaces and newlines into \n; the check compares the escaped form
    assert ra.english_mismatch([('t/a', 'A\\nB', '가')], {'t/a': 'A\nB'}) == []
