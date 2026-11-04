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
