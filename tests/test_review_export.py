"""Tests for tools/review_export.py: review sheets for translation review (GPT / human), one chunk per table."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import review_export as rx

SRC = {'swat.strtbl/a': dict(id='swat.strtbl/a', table='swat.strtbl', src='Go\nnow', font='berrylium'),
       'swat.strtbl/b': dict(id='swat.strtbl/b', table='swat.strtbl', src='Press {BTN_BD}', font='berrylium'),
       'lvl_x.strtbl/c': dict(id='lvl_x.strtbl/c', table='lvl_x.strtbl', src='Hi', font='berrylium')}
RECS = [dict(id='swat.strtbl/a', ko='가\n자'), dict(id='swat.strtbl/b', ko='{BTN_BD} 누르기'),
        dict(id='lvl_x.strtbl/c', same_as='swat.strtbl/a')]


def test_rows_skip_same_as_and_escape_newlines():
    rows = rx.rows(SRC, RECS)
    assert [r['id'] for r in rows] == ['swat.strtbl/a', 'swat.strtbl/b']
    assert rows[0]['en'] == 'Go\\nnow' and rows[0]['ko'] == '가\\n자'


def test_chunks_split_by_table_and_size():
    rows = rx.rows(SRC, RECS)
    cs = rx.chunks(rows, size=1)
    assert [(name, len(r)) for name, r in cs] == [('swat.strtbl-01', 1), ('swat.strtbl-02', 1)]


def test_tsv_round_trips_back_to_batch():
    rows = rx.rows(SRC, RECS)
    text = rx.to_tsv(rows)
    assert text.splitlines()[0] == 'id\ten\tko'
    assert rx.from_tsv(text) == {'swat.strtbl/a': '가\n자', 'swat.strtbl/b': '{BTN_BD} 누르기'}
