"""Tests for dave_patch.insert: add named entries to a 'Dave' archive keeping name order."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import dave, dave_patch, davename, iso9660

ISO = os.path.join(ROOT, 'orig/Red Dead Revolver (USA).iso')
need = pytest.mark.skipif(not os.path.exists(ISO), reason='source ISO not present')


def front():
    img = open(ISO, 'rb').read()
    _, lba, size = iso9660.find(img, 'FRONT.DAT')
    return img[lba * 2048: lba * 2048 + size]


def by_name(d):
    _, _, ents, _, _ = dave.read_dave_bytes(d)
    return dict(zip(davename.names_of(d), (dave.entry_data(d, e) for e in ents)))


@need
def test_insert_keeps_all_entries_and_order():
    src = front()
    new = {'berrylium_06.tex': b'\x11' * 5000, 'berrylium_07.tex': b'\x22' * 300}
    out = dave_patch.insert(src, new)
    before, after = by_name(src), by_name(out)
    assert set(after) == set(before) | set(new)
    for k, v in before.items(): assert after[k] == v, k
    for k, v in new.items(): assert after[k] == v
    names = davename.names_of(out)
    assert names == sorted(names)
    assert names.index('berrylium_06.tex') == names.index('berrylium_05.tex') + 1
    assert out[:4] == b'Dave' and len(out) % 0x800 == 0


@need
def test_insert_rejects_existing_name():
    with pytest.raises(ValueError):
        dave_patch.insert(front(), {'berrylium_00.tex': b'x'})


@need
def test_insert_nothing_is_identity():
    src = front()
    assert dave_patch.insert(src, {}) == src


@need
def test_insert_grows_capacity_when_toc_full():
    img = open(ISO, 'rb').read()
    _, lba, size = iso9660.find(img, 'LVLS_SNG/WOODS.DAT')
    src = img[lba * 2048: lba * 2048 + size]
    new = {'berrylium_%02d.tex' % i: bytes([i]) * 1000 for i in range(6, 16)}
    out = dave_patch.insert(src, new)
    before, after = by_name(src), by_name(out)
    assert set(after) == set(before) | set(new)
    for k, v in before.items(): assert after[k] == v, k
    names = davename.names_of(out)
    assert names == sorted(names)
