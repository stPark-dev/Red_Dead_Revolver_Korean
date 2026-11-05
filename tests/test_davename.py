"""Tests for tools/davename.py (packed 6-bit, prefix-shared entry names of 'Dave' archives)."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import davename, dave, iso9660

ISO = os.path.join(ROOT, 'orig/Red Dead Revolver (USA).iso')
need = pytest.mark.skipif(not os.path.exists(ISO), reason='source ISO not present')


def archive(name):
    img = open(ISO, 'rb').read()
    _, lba, size = iso9660.find(img, name)
    return img[lba * 2048: lba * 2048 + size]


def test_encode_decode_roundtrip():
    names = ['arial14.fonttex', 'arial14_00.tex', 'b (2) of-x.cm', 'a~b.txt', 'berrylium.fonttex']
    blob, offs = davename.encode(names)
    assert davename.decode_all(blob + b'\0' * 64, offs) == names


def test_prefix_copy_matches_game_encoding():
    # bytes taken from FRONT.DAT entries 5 and 6
    assert davename.decode(bytes.fromhex('794829ca81662c00'), 'berrylium.fonttex') == 'berrylium_00.tex'
    assert davename.encode_one('berrylium_01.tex', 'berrylium_00.tex') == bytes.fromhex('7bb81c68c602')


def test_unknown_char_rejected():
    with pytest.raises(KeyError):
        davename.encode(['bad!name'])


@need
def test_front_names_known():
    names = davename.names_of(archive('FRONT.DAT'))
    assert names[0] == 'arial14.fonttex'
    assert names[4] == 'berrylium.fonttex'
    assert names[5:11] == ['berrylium_%02d.tex' % i for i in range(6)]
    assert names == sorted(names)


@need
@pytest.mark.parametrize('arc', ['FRONT.DAT', 'SWAT.DAT', 'LVLS_SNG/SALOON.DAT'])
def test_reencoded_names_decode_identically(arc):
    names = davename.names_of(archive(arc))
    blob, offs = davename.encode(names)
    assert davename.decode_all(blob + b'\0' * 64, offs) == names


def _full_name_gaps(blob, offs):
    full = [i for i, o in enumerate(offs) if blob[o] & 63 < 56]
    return full, [b - a for a, b in zip(full, full[1:])] + [len(offs) - full[-1]]


def test_encode_restarts_full_name_within_32_entries():
    # original archives never chain more than 31 prefix-copied names after a full name (max gap 32);
    # longer chains made the game fail lookups in SWAT.DAT (slow loads, crash in chapter 21)
    names = ['hud_w_%03d.tex' % i for i in range(200)]
    blob, offs = davename.encode(names)
    full, gaps = _full_name_gaps(blob, offs)
    assert full[0] == 0 and max(gaps) <= 32
    assert davename.decode_all(blob + b'\0' * 64, offs) == names


@need
def test_encode_swat_names_keeps_original_chain_limit():
    names = davename.names_of(archive('SWAT.DAT'))
    blob, offs = davename.encode(names)
    assert max(_full_name_gaps(blob, offs)[1]) <= 32
    assert davename.decode_all(blob + b'\0' * 64, offs) == names
