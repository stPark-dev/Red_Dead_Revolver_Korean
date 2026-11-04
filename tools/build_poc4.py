"""PoC4: add a NEW texture page (berrylium_06.tex) holding Hangul glyphs, inserted by name.

usage: build_poc4.py out.iso targets.json [chars]
"""
import sys, hashlib, json
sys.path.insert(0, 'tools')
import dave, dave_patch, davename, strtbl, iso9660, fontb
from build_poc3 import render_cell, alpha_index_map, SRC_ISO, SRC_SHA1

ARCHIVES = ['FRONT.DAT', 'SWAT.DAT']
FONT = 'berrylium'
CELL_W, CELL_H, YOFF = 20, 21, -19


def new_page(template, chars):
    pg = fontb.parse_page(template)
    pg['pixels'] = bytearray(len(pg['pixels']))
    amap = alpha_index_map(pg)
    glyphs = []
    per_row = pg['w'] // CELL_W
    for i, ch in enumerate(chars):
        x, y = (i % per_row) * CELL_W, (i // per_row) * CELL_H
        assert y + CELL_H <= pg['h'], 'page full'
        cell = render_cell(ch, CELL_W, CELL_H)
        for yy in range(CELL_H):
            for xx in range(CELL_W):
                pg['pixels'][(y + yy) * pg['w'] + x + xx] = amap[cell.getpixel((xx, yy))]
        glyphs.append(dict(code=ord(ch), x=x, y=y, w=CELL_W, h=CELL_H, yoff=YOFF))
    return fontb.build_page(pg), glyphs


def patch_archive(raw, targets, chars):
    d, _, ents, _, _ = dave.read_dave_bytes(raw)
    names = davename.names_of(d)
    idx = {n: i for i, n in enumerate(names)}
    reps = {}
    for e in ents:
        data = dave.entry_data(d, e)
        if data[:4] != b'\x0a\0\0\0': continue
        try: t = strtbl.parse(data)
        except Exception: continue
        hit = 0
        for lang in t['langs']:
            if lang is None: continue
            for x in lang[0]:
                if x['text'] in targets: x['text'] = targets[x['text']]; hit += 1
        if hit: reps[e['idx']] = strtbl.build(t)
    desc = fontb.parse(dave.entry_data(d, ents[idx[FONT + '.fonttex']]))
    npages = len(desc['pages'])
    template = dave.entry_data(d, ents[idx['%s_%02d.tex' % (FONT, npages - 1)]])
    page, glyphs = new_page(template, chars)
    for i, g in enumerate(glyphs):
        desc = fontb.add_glyph(desc, g, new_page=(i == 0))
    reps[idx[FONT + '.fonttex']] = fontb.build(desc)
    out = dave_patch.patch(raw, reps)
    return dave_patch.insert(out, {'%s_%02d.tex' % (FONT, npages): page}), sorted(reps)


def main(out, targets_path, chars):
    targets = json.load(open(targets_path, encoding='utf-8'))
    img = bytearray(open(SRC_ISO, 'rb').read())
    assert hashlib.sha1(img).hexdigest() == SRC_SHA1, 'source ISO mismatch'
    for arc in ARCHIVES:
        _, lba, size = iso9660.find(img, arc)
        new, reps = patch_archive(bytes(img[lba * 2048: lba * 2048 + size]), targets, chars)
        print(arc, 'replaced', reps, iso9660.replace(img, arc, new))
    iso9660.finalize(img)
    open(out, 'wb').write(img)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '가나다라마바사')
