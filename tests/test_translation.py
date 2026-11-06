"""Tests for tools/translation.py: translation records, mechanical checks, selection policy."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import translation as tr

SRC = {
    'swat.strtbl/a': dict(id='swat.strtbl/a', font='berrylium', src='Press {BTN_BD} to go'),
    'swat.strtbl/b': dict(id='swat.strtbl/b', font='berrylium', src='Hello\nthere'),
    'lvl_x.strtbl/b': dict(id='lvl_x.strtbl/b', font='berrylium', src='Hello\nthere'),
    'swat.strtbl/e': dict(id='swat.strtbl/e', font='berrylium', src=''),
}


def rec(i, ko=None, state='needs_review', **kw):
    return dict(id=i, src=SRC[i]['src'], ko=ko, state=state, **kw)


def test_check_ok_and_token_mismatch():
    assert tr.check(SRC, [rec('swat.strtbl/a', '{BTN_BD} 버튼을 눌러 이동')]) == []
    errs = tr.check(SRC, [rec('swat.strtbl/a', '버튼을 눌러 이동')])
    assert any('token' in e for e in errs)


def test_check_detects_stale_source_and_unknown_id():
    errs = tr.check(SRC, [dict(id='swat.strtbl/a', src='old', ko='x', state='needs_review'),
                          dict(id='nope', src='', ko='x', state='needs_review')])
    assert any('source changed' in e for e in errs) and any('unknown id' in e for e in errs)


def test_check_same_as_and_duplicates():
    ok = [rec('swat.strtbl/b', '안녕\n하세요'), dict(id='lvl_x.strtbl/b', src='Hello\nthere', same_as='swat.strtbl/b',
                                                      state='needs_review')]
    assert tr.check(SRC, ok) == []
    bad = ok + [rec('swat.strtbl/b', '중복')]
    assert any('duplicate' in e for e in tr.check(SRC, bad))
    dangling = [dict(id='lvl_x.strtbl/b', src='Hello\nthere', same_as='swat.strtbl/zz', state='needs_review')]
    assert any('same_as' in e for e in tr.check(SRC, dangling))


def test_check_rejects_bad_state_and_unsupported_punct():
    assert any('state' in e for e in tr.check(SRC, [rec('swat.strtbl/b', '안녕', state='done')]))
    assert any('U+2026' in e for e in tr.check(SRC, [rec('swat.strtbl/b', '안녕…')]))


def test_select_dev_policy_falls_back_to_source():
    recs = [rec('swat.strtbl/a', '{BTN_BD} 이동', state='in_progress')]
    out = tr.select(SRC, recs, policy='dev')
    assert out['swat.strtbl/a'] == '½ 이동'
    assert out['swat.strtbl/b'] == 'Hello\nthere'  # untranslated -> source preserved
    assert out['swat.strtbl/e'] == ''


def test_select_release_policy_requires_eligible():
    ko = {'swat.strtbl/a': '{BTN_BD} x', 'swat.strtbl/e': ''}
    recs = [rec(i, ko.get(i, 'x'), state='distribution_eligible') for i in SRC]
    out = tr.select(SRC, recs, policy='release')
    assert out['swat.strtbl/a'] == '\u00bd x'
    with pytest.raises(ValueError):
        tr.select(SRC, recs[:1], policy='release')


def test_select_resolves_same_as():
    recs = [rec('swat.strtbl/b', '안녕\n하세요'),
            dict(id='lvl_x.strtbl/b', src='Hello\nthere', same_as='swat.strtbl/b', state='needs_review')]
    assert tr.select(SRC, recs, policy='dev')['lvl_x.strtbl/b'] == '안녕\n하세요'


def test_merge_adds_records_with_baseline_src_and_links_duplicates():
    recs = tr.merge(SRC, [], {'swat.strtbl/b': '안녕\n하세요'}, state='needs_review')
    by = {r['id']: r for r in recs}
    assert by['swat.strtbl/b'] == dict(id='swat.strtbl/b', src='Hello\nthere', ko='안녕\n하세요', state='needs_review')
    assert by['lvl_x.strtbl/b'] == dict(id='lvl_x.strtbl/b', src='Hello\nthere', same_as='swat.strtbl/b',
                                        state='needs_review')
    assert tr.check(SRC, recs) == []


def test_merge_refuses_to_overwrite_existing_translation():
    recs = tr.merge(SRC, [], {'swat.strtbl/b': '하나'}, state='needs_review')
    with pytest.raises(ValueError):
        tr.merge(SRC, recs, {'swat.strtbl/b': '둘'}, state='needs_review')
    out = tr.merge(SRC, recs, {'swat.strtbl/b': '둘'}, state='needs_review', replace=True)
    assert {r['id']: r for r in out}['swat.strtbl/b']['ko'] == '둘'


def test_select_beta_policy_falls_back_like_dev_but_rejects_unfinished_drafts():
    recs = [rec('swat.strtbl/a', '{BTN_BD} 이동', state='needs_review')]
    out = tr.select(SRC, recs, policy='beta')
    assert out['swat.strtbl/a'] == '½ 이동' and out['swat.strtbl/b'] == 'Hello\nthere'
    with pytest.raises(ValueError, match='not ready for beta'):
        tr.select(SRC, [rec('swat.strtbl/a', '{BTN_BD} 이동', state='in_progress')], policy='beta')
