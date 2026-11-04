"""Tests for tools/extract_strtbl.py (strtbl population -> translation source baseline)."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import extract_strtbl as ex, strtbl


def table(pairs, font='berrylium'):
    keys = sorted(k for k, _ in pairs)
    ents = [dict(hash=strtbl.elf_hash(k), a=1, b=0, font=font, text=v, sx=0.8, sy=0.8, tail=0) for k, v in pairs]
    return dict(keys=keys, langs=[(ents, 0)])


def test_collect_merges_copies_and_tokenizes():
    found = [('FRONT.DAT', 240, 'swat.strtbl', table([('a', 'Press ½'), ('b', 'Hi')])),
             ('LVLS_SNG/X.DAT', 9, 'swat.strtbl', table([('a', 'Press ½'), ('b', 'Hi')])),
             ('LVLS_SNG/X.DAT', 10, 'lvl_x.strtbl', table([('a', 'Go')]))]
    ents, excluded = ex.collect(found)
    assert [e['id'] for e in ents] == ['lvl_x.strtbl/a', 'swat.strtbl/a', 'swat.strtbl/b']
    a = ents[1]
    assert a['src'] == 'Press {BTN_BD}' and a['font'] == 'berrylium'
    assert a['copies'] == ['FRONT.DAT#240', 'LVLS_SNG/X.DAT#9']
    assert excluded == []


def test_collect_rejects_conflicting_copies():
    found = [('A.DAT', 1, 't.strtbl', table([('a', 'x')])), ('B.DAT', 1, 't.strtbl', table([('a', 'y')]))]
    with pytest.raises(ValueError):
        ex.collect(found)


def test_collect_excludes_backup_and_xbox_tables():
    found = [('SWAT.DAT', 1, 'backup_swat.strtbl', table([('a', 'x')])),
             ('SWAT.DAT', 2, 'xb_swat.strtbl', table([('a', 'x')])),
             ('SWAT.DAT', 3, 'swat_xbx.strtbl', table([('a', 'x')])),
             ('SWAT.DAT', 4, 'swat.bak.strtbl', table([('a', 'x')]))]
    ents, excluded = ex.collect(found)
    assert ents == [] and len(excluded) == 4


def test_reach_marks_swat_only_tables():
    found = [('SWAT.DAT', 5, 'lvl_tng.strtbl', table([('a', 'x')]))]
    ents, _ = ex.collect(found)
    assert ents[0]['reach'] == 'swat-only'
