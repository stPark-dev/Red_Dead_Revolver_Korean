"""Tests for tools/strtbl.py (string tables, ELF-hashed keys, UTF-16 text)."""
import glob, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import strtbl

FRONT_TBL = os.path.join(ROOT, 'work/x/FRONT/0240.bin')  # swat.strtbl
need = pytest.mark.skipif(not os.path.exists(FRONT_TBL), reason='extracted FRONT.DAT not present')


def test_elf_hash_known_values():
    assert strtbl.elf_hash('controller_shoot') == 0x0dfd82f4
    assert strtbl.elf_hash('') == 0


@need
def test_roundtrip_all_parseable_copies():
    n = 0
    for p in glob.glob(os.path.join(ROOT, 'work/x/*/*.bin')):
        b = open(p, 'rb').read()
        if b[:4] != b'\x0a\0\0\0': continue
        try: t = strtbl.parse(b)
        except Exception: continue
        assert strtbl.build(t) == b, p
        n += 1
    assert n > 100


@need
def test_entries_by_key():
    t = strtbl.parse(open(FRONT_TBL, 'rb').read())
    ents = strtbl.entries_by_key(t)
    assert len(ents) == 1181
    assert ents['controller_shoot']['text'] == 'Shoot'
    assert ents['controller_shoot']['font'] == 'berrylium'


def test_entries_by_key_rejects_unmatched_hash():
    t = dict(keys=['a'], langs=[([dict(hash=123, text='x')], 0)])
    with pytest.raises(ValueError):
        strtbl.entries_by_key(t)


def test_add_entries_inserts_sorted_keys_and_hashed_entries():
    t = dict(nlang=1, loffs=(0,), nbuck=512, keys=['a', 'c'],
             langs=[([dict(hash=strtbl.elf_hash('a'), a=1, b=0, font='berrylium', text='A', sx=0.8, sy=0.8, tail=0),
                      dict(hash=strtbl.elf_hash('c'), a=1, b=0, font='berrylium', text='C', sx=0.8, sy=0.8, tail=0)],
                     0)])
    t2 = strtbl.add_entries(t, {'b': ('berrylium', '비')})
    assert t2['keys'] == ['a', 'b', 'c'] and t['keys'] == ['a', 'c']
    ents = strtbl.entries_by_key(t2)
    assert ents['b']['text'] == '비' and ents['b']['sx'] == 1.0
    assert strtbl.parse(strtbl.build(t2))['keys'] == ['a', 'b', 'c']
    with pytest.raises(ValueError):
        strtbl.add_entries(t, {'a': ('berrylium', 'x')})
