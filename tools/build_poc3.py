"""PoC3: show '가' through the HUD (UTF-16) renderer by adding a U+AC00 glyph to font B.

usage: build_poc3.py out.iso targets.json
targets.json maps original strtbl strings to replacements (UTF-16 text, no hook needed).
"""
import sys, hashlib, json, os
sys.path.insert(0, 'tools')
from PIL import Image, ImageDraw, ImageFont
import dave, dave_patch, strtbl, iso9660, fontb

SRC_ISO = 'orig/Red Dead Revolver (USA).iso'
SRC_SHA1 = '7bbe502a1b170f80e378a566ad8ec313dba78361'
ARCHIVES = ['FRONT.DAT', 'SWAT.DAT']
FONT_PATH = '../fonts/NotoSerifKR-Bold.otf'
HUD_FONT_MD5 = '77969744'  # FRONT/0004 family (64 copies)
CH, CELL = '가', dict(x=40, y=0, w=20, h=21, yoff=-19)


def render_cell(ch, w, h):
    im = Image.new('L', (w, h), 0)
    ft = ImageFont.truetype(FONT_PATH, h - 1)
    l, t, r, b = ft.getbbox(ch)
    ImageDraw.Draw(im).text(((w - (r - l)) // 2 - l, (h - (b - t)) // 2 - t), ch, 255, font=ft)
    return im


def alpha_index_map(pg):
    """index of the palette entry (white ramp) whose alpha is nearest to each coverage 0..255."""
    ramp = [(c[3], i) for i, c in enumerate(pg['palette']) if c[:3] == (0xf7, 0xf7, 0xf7)] + [(0, 0)]
    return [min(ramp, key=lambda r: abs(r[0] - v))[1] for v in range(256)]


def add_hangul(desc, page):
    f = fontb.parse(desc)
    g = fontb.add_glyph(f, dict(code=ord(CH), **CELL))
    pg = fontb.parse_page(page)
    amap = alpha_index_map(pg)
    cell = render_cell(CH, CELL['w'], CELL['h'])
    for yy in range(CELL['h']):
        for xx in range(CELL['w']):
            pg['pixels'][(CELL['y'] + yy) * pg['w'] + CELL['x'] + xx] = amap[cell.getpixel((xx, yy))]
    return fontb.build(g), fontb.build_page(pg)


def main(out, targets_path):
    targets = json.load(open(targets_path, encoding='utf-8'))
    img = bytearray(open(SRC_ISO, 'rb').read())
    assert hashlib.sha1(img).hexdigest() == SRC_SHA1, 'source ISO mismatch'
    for arc in ARCHIVES:
        _, lba, size = iso9660.find(img, arc)
        raw = bytes(img[lba * 2048: lba * 2048 + size])
        d, _, ents, _, _ = dave.read_dave_bytes(raw)
        byidx = {e['idx']: e for e in ents}
        reps = {}
        for e in ents:
            data = dave.entry_data(d, e)
            if hashlib.md5(data).hexdigest().startswith(HUD_FONT_MD5):
                last = e['idx'] + 6
                reps[e['idx']], reps[last] = add_hangul(data, dave.entry_data(d, byidx[last]))
            elif data[:4] == b'\x0a\0\0\0':
                try: t = strtbl.parse(data)
                except Exception: continue
                hit = 0
                for lang in t['langs']:
                    if lang is None: continue
                    for x in lang[0]:
                        if x['text'] in targets: x['text'] = targets[x['text']]; hit += 1
                if hit: reps[e['idx']] = strtbl.build(t)
        print(arc, 'modified entries', sorted(reps))
        if reps: print(arc, iso9660.replace(img, arc, dave_patch.patch(raw, reps)))
    iso9660.finalize(img)
    open(out, 'wb').write(img)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
