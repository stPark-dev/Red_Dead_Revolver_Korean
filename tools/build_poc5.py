"""PoC5: Hangul in in-game subtitles (global strtbl, berrylium) incl. word wrap, loaded from a level DAT.

New berrylium page is added to FRONT/SWAT/PERFNEW (level 1).
usage: build_poc5.py out.iso [grow]   (grow: also insert 200 dummy entries into PERFNEW to force TOC growth)
"""
import sys, hashlib
sys.path.insert(0, 'tools')
import iso9660, dave_patch
from build_poc3 import SRC_ISO, SRC_SHA1
from build_poc4 import patch_archive

CHARS = '가나다라마바사'
TARGETS = {
    'There’s a target practice area for you to try out your pa’s pistol. ':
        '가나다라 마바사 가나다라 마바사 A가B 가나다라 마바사 가나다라 마바사 가나다',
    'Follow the fenced path down to the creek bed to learn how to shoot.': '마바사, 가나다라!',
}
ARCHIVES = ['FRONT.DAT', 'SWAT.DAT', 'LVLS_SNG/PERFNEW.DAT']


def main(out, grow=False):
    img = bytearray(open(SRC_ISO, 'rb').read())
    assert hashlib.sha1(img).hexdigest() == SRC_SHA1, 'source ISO mismatch'
    for arc in ARCHIVES:
        _, lba, size = iso9660.find(img, arc)
        new, reps = patch_archive(bytes(img[lba * 2048: lba * 2048 + size]), TARGETS, CHARS)
        if grow and arc.endswith('PERFNEW.DAT'):
            new = dave_patch.insert(new, {'zzdummy_%03d.bin' % i: bytes([i]) * 64 for i in range(200)})
        print(arc, 'replaced', len(reps), iso9660.replace(img, arc, new))
    iso9660.finalize(img)
    open(out, 'wb').write(img)


if __name__ == '__main__':
    main(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == 'grow')
