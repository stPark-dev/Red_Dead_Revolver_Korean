"""Tests for tools/iso9660.py file listing."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import iso9660

ISO = os.path.join(ROOT, 'orig/Red Dead Revolver (USA).iso')


@pytest.mark.skipif(not os.path.exists(ISO), reason='source ISO not present')
def test_list_files():
    img = open(ISO, 'rb').read()
    files = iso9660.list_files(img)
    paths = [p for p, _, _ in files]
    assert 'FRONT.DAT' in paths and 'LVLS_SNG/WOODS.DAT' in paths and 'SYSTEM.CNF' in paths
    assert len(paths) == 103
    p, lba, size = next(f for f in files if f[0] == 'FRONT.DAT')
    assert iso9660.find(img, 'FRONT.DAT')[1:] == (lba, size)


# --- replace_all: keep the original file order and locality (no appending at the image end) ---
import struct
SEC = iso9660.SEC


def _rec(name, lba, size, is_dir=False):
    n = name.encode() if name in ('\0', '\1') else (name + ('' if is_dir else ';1')).encode()
    ln = 33 + len(n) + (len(n) + 1) % 2
    r = bytearray(ln); r[0] = ln
    struct.pack_into('<I', r, 2, lba); struct.pack_into('>I', r, 6, lba)
    struct.pack_into('<I', r, 10, size); struct.pack_into('>I', r, 14, size)
    r[25] = 2 if is_dir else 0; r[32] = len(n); r[33:33 + len(n)] = n
    return bytes(r)


def make_iso(files, root_lba=18, total=None):
    """files: [(name, lba, data)] in the root directory."""
    end = max(l + (len(d) + SEC - 1) // SEC for _, l, d in files)
    total = total or end
    img = bytearray(total * SEC)
    img[16 * SEC] = 1; img[16 * SEC + 1:16 * SEC + 6] = b'CD001'
    struct.pack_into('<I', img, 16 * SEC + 80, total); struct.pack_into('>I', img, 16 * SEC + 84, total)
    img[16 * SEC + 156:16 * SEC + 190] = _rec('\0', root_lba, SEC, True)
    d = _rec('\0', root_lba, SEC, True) + _rec('\1', root_lba, SEC, True)
    for name, lba, data in files:
        d += _rec(name, lba, len(data)); img[lba * SEC:lba * SEC + len(data)] = data
    img[root_lba * SEC:root_lba * SEC + len(d)] = d
    return img


def _content(img):
    return {p: bytes(img[l * SEC:l * SEC + s]) for p, l, s in iso9660.list_files(img)}


def test_replace_all_grow_shifts_only_later_files():
    a, b, c = b'A' * 3000, b'B' * 5000, b'C' * 100
    img = make_iso([('A', 20, a), ('B', 22, b), ('C', 25, c)])   # B: 3 sectors, ends at 25
    new_b = b'N' * (5 * SEC + 1)                                   # 6 sectors: grows by 3
    iso9660.replace_all(img, {'B': new_b})
    lbas = {p: l for p, l, _ in iso9660.list_files(img)}
    assert lbas == {'A': 20, 'B': 22, 'C': 28}
    assert _content(img) == {'A': a, 'B': new_b, 'C': c}
    assert struct.unpack_from('<I', img, 16 * SEC + 80)[0] * SEC == len(img)
    assert struct.unpack_from('>I', img, 16 * SEC + 84)[0] * SEC == len(img)


def test_replace_all_same_size_stays_in_place():
    img = make_iso([('A', 20, b'A' * 3000), ('B', 22, b'B' * 100)])
    before = len(img)
    iso9660.replace_all(img, {'A': b'X' * 4096})
    assert {p: l for p, l, _ in iso9660.list_files(img)} == {'A': 20, 'B': 22}
    assert len(img) == before and _content(img)['A'] == b'X' * 4096


def test_replace_all_uses_gap_before_next_file():
    img = make_iso([('A', 20, b'A' * 100), ('B', 30, b'B' * 100)])  # 9 free sectors after A
    iso9660.replace_all(img, {'A': b'Y' * (5 * SEC)})
    assert {p: l for p, l, _ in iso9660.list_files(img)} == {'A': 20, 'B': 30}


def test_replace_all_keeps_data_after_last_file():
    img = make_iso([('A', 20, b'A' * 100), ('B', 21, b'B' * 100)], total=24)
    img[23 * SEC:23 * SEC + 4] = b'TAIL'
    iso9660.replace_all(img, {'A': b'Z' * (2 * SEC)})
    assert img[24 * SEC:24 * SEC + 4] == b'TAIL'


def test_replace_all_rejects_directory_after_moved_file():
    img = make_iso([('A', 20, b'A' * 100), ('B', 21, b'B' * 100)], root_lba=22, total=23)
    with pytest.raises(ValueError):
        iso9660.replace_all(img, {'A': b'Z' * (3 * SEC)})
