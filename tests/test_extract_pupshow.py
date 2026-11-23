"""Tests for tools/extract_pupshow.py: which subtitle files are translation targets.

Besides level cutscenes (lvl_*_pupshow_*_en.txt) the FMV movies PSS/<NAME>.PSS show subtitles from
'<name>_en.txt' in SWAT.DAT (chapter 3 'How much for the lot?' stayed English in game, 2026-11-05)."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import extract_pupshow as ep, pupshow, dave, davename, iso9660

ISO = os.path.join(ROOT, 'orig/Red Dead Revolver (USA).iso')
need = pytest.mark.skipif(not os.path.exists(ISO), reason='source ISO not present')
MOVIES = {'sher7001', 'tng01', 'coach02'}


def test_level_cutscene_files_selected():
    assert ep.is_subtitle('lvl_bank_pupshow_01_en.txt', MOVIES)


def test_movie_subtitle_files_selected():
    assert ep.is_subtitle('sher7001_en.txt', MOVIES) and ep.is_subtitle('tng01_en.txt', MOVIES)


def test_key_based_level_subtitles_selected():
    # Brimstone townsfolk (lvl_tomb), train robbery (lvl_traincar) ... stayed English in game (user report 2026-11-23)
    assert ep.is_subtitle('lvl_tomb_subtitles_en.txt', MOVIES) and ep.is_subtitle('lvl_traincar_subtitles_en.txt', MOVIES)


def test_key_based_cues_drop_keys_the_string_table_shows():
    # a key present in a string table is drawn from the string table, not the file (docs/survey.md)
    recs = [dict(id='p/a/0', cue_key='K1'), dict(id='p/a/1', cue_key='K2'), dict(id='p/b/0')]
    assert [r['id'] for r in ep.drop_strtbl_keys(recs, {'K1'})] == ['p/a/1', 'p/b/0']


def test_unconsumed_files_skipped():
    # test/orphan files have no movie
    for n in ('testsubtitles_en.txt', 'jail01_en.txt', '1_en.txt', 'sher7001.txt'):
        assert not ep.is_subtitle(n, MOVIES), n


@need
def test_movie_subtitles_round_trip_exact():
    img = open(ISO, 'rb').read()
    movies = ep.movie_names(img)
    assert {'sher7001', 'tng01', 'diegocar'} <= movies
    _, lba, size = iso9660.find(img, 'SWAT.DAT')
    raw = img[lba * 2048: lba * 2048 + size]
    d, _, ents, _, _ = dave.read_dave_bytes(raw)
    n = 0
    for name, e in zip(davename.names_of(d), ents):
        if name.endswith('_en.txt') and '_pupshow_' not in name and '_subtitles_' not in name and ep.is_subtitle(name, movies):
            b = dave.entry_data(d, e)
            assert pupshow.build(pupshow.parse(b)) == b, name
            n += 1
    assert n == 17


def test_reach_movie_subtitles_are_game_even_if_only_in_swat():
    assert ep.reach('sher7001_en.txt', ['SWAT.DAT#1'], MOVIES) == 'game'
    assert ep.reach('lvl_msn_pupshow_01_en.txt', ['SWAT.DAT#1'], MOVIES) == 'swat-only'
    assert ep.reach('lvl_msn_pupshow_01_en.txt', ['SWAT.DAT#1', 'LVLS_SNG/MSN.DAT#3'], MOVIES) == 'game'
