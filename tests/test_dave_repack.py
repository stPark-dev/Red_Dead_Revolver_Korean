"""Tests for dave_patch.repack: lay patched entry data out in the original data order.

Appending replaced/new entry data at the archive end made the level loader seek back and forth
(chapter 21 'End of the Line' loaded 5x slower and crashed, docs/survey.md)."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import dave, dave_patch, davename, iso9660

ISO = os.path.join(ROOT, 'orig/Red Dead Revolver (USA).iso')
need = pytest.mark.skipif(not os.path.exists(ISO), reason='source ISO not present')


def archive(path):
    img = open(ISO, 'rb').read()
    _, lba, size = iso9660.find(img, path)
    return img[lba * 2048: lba * 2048 + size]


def by_name(d):
    _, _, ents, _, _ = dave.read_dave_bytes(d)
    return dict(zip(davename.names_of(d), (dave.entry_data(d, e) for e in ents)))


def data_order(d):
    _, _, ents, _, _ = dave.read_dave_bytes(d)
    names = davename.names_of(d)
    return [names[e['idx']] for e in sorted(ents, key=lambda e: (e['off'], e['idx']))]


@need
@pytest.mark.parametrize('path', ['LVLS_SNG/TRAIN.DAT', 'SWAT.DAT'])
def test_repack_of_original_is_identity(path):
    src = archive(path)
    assert dave_patch.repack(src, src) == src


@need
def test_repack_keeps_original_order_and_contents():
    src = archive('LVLS_SNG/TRAIN.DAT')
    names = davename.names_of(src)
    i_font = names.index('berrylium.fonttex')
    patched = dave_patch.patch(src, {i_font: b'F' * 9000})
    patched = dave_patch.insert(patched, {'berrylium_06.tex': b'\x11' * 5000, 'berrylium_07.tex': b'\x22' * 300})
    out = dave_patch.repack(src, patched)
    assert by_name(out) == by_name(patched)
    order = data_order(out)
    old = [n for n in order if n in set(names)]
    assert old == data_order(src)                       # original entries keep their data order
    last_page = max(n for n in names if n.startswith('berrylium_') and n.endswith('.tex'))
    k = order.index(last_page)
    assert order[k + 1:k + 3] == ['berrylium_06.tex', 'berrylium_07.tex']
    assert len(out) % 0x800 == 0 and len(out) < len(patched) + 0x10000


@need
def test_repack_rejects_changed_alias_entry():
    src = archive('SWAT.DAT')
    names = davename.names_of(src)
    _, _, ents, _, _ = dave.read_dave_bytes(src)
    srt = sorted(ents, key=lambda e: (e['off'], e['idx']))
    alias = next(srt[k + 1] for k in range(len(srt) - 1) if srt[k + 1]['off'] == srt[k]['off'])
    patched = dave_patch.patch(src, {alias['idx']: b'x' * 100})
    with pytest.raises(ValueError):
        dave_patch.repack(src, patched)
