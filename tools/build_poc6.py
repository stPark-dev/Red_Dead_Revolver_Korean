"""PoC6 (memory stress): as many KS X 1001 syllables as fit in the 24-page limit, added to berrylium,
damaged and regulatorcondensed as 4bpp 256x256 pages, in FRONT/SWAT/PERFNEW.
Menu entries are moved onto the other fonts to see them; each shows the last glyph of its font.

usage: build_poc6.py out.iso [fonts=berrylium,damaged,regulatorcondensed] [page=256] [bpp=4] [maxnew=24]
"""
import sys, hashlib
sys.path.insert(0, 'tools')
from PIL import Image, ImageDraw, ImageFont
import dave, dave_patch, davename, strtbl, iso9660, fontb, fontgen
from build_poc3 import SRC_ISO, SRC_SHA1

KSX = [bytes([a, b]).decode('euc-kr') for a in range(0xB0, 0xC9) for b in range(0xA1, 0xFF)]
FONTS = {  # name: (cell, yoff, ttf)
    'berrylium': ((22, 22), -20, '../fonts/NotoSerifKR-Bold.otf'),
    'damaged': ((32, 32), -36, '../fonts/NotoSerifKR-Black.otf'),
    'regulatorcondensed': ((24, 26), -23, '../fonts/NotoSansKR-Bold.otf'),
}
TARGETS = {  # original text -> (font or None, new text); {last} = last glyph added to that font
    'New': (None, '가나다 {last}'),
    'Change Player': ('damaged', '가나다 {last}'),
    'Player Options': ('regulatorcondensed', '가나다 {last}'),
    'There’s a target practice area for you to try out your pa’s pistol. ':
        (None, '저 아래에 사격 연습장이 있다. 아버지의 권총을 시험해 보거라. {last}'),
}
ARCHIVES = ['FRONT.DAT', 'SWAT.DAT', 'LVLS_SNG/PERFNEW.DAT']


def renderer(ttf):
    def render(ch, w, h):
        im = Image.new('L', (w, h), 0)
        ft = ImageFont.truetype(ttf, h - 2)
        l, t, r, b = ft.getbbox(ch)
        ImageDraw.Draw(im).text(((w - (r - l)) // 2 - l, (h - (b - t)) // 2 - t), ch, 255, font=ft)
        return im
    return render


def make_fonts(raw, cfg):
    d, _, ents, _, _ = dave.read_dave_bytes(raw)
    names = davename.names_of(d)
    get = lambda n: dave.entry_data(d, ents[names.index(n)])
    pal = fontb.parse_page(get('regulatorcondensed_00.tex' if cfg['bpp'] == 4 else 'berrylium_00.tex'))['palette']
    out, ps = {}, cfg['page']
    for f in cfg['fonts']:
        cell, yoff, ttf = FONTS[f]
        src = get(f + '.fonttex')
        npg = min(cfg['maxnew'], fontb.MAX_PAGES - len(fontb.parse(src)['pages']))
        cap = npg * (ps // cell[0]) * (ps // cell[1])
        desc, pages = fontgen.add_pages(fontb.parse(src), KSX[:cap], cell, yoff, (ps, ps), cfg['bpp'], pal,
                                        renderer(ttf))
        assert len(desc['pages']) <= 48, f
        out[f] = (src, fontb.build(desc), pages, KSX[:cap][-1])
        print(f, 'pages', len(desc['pages']), 'glyphs', min(cap, len(KSX)), 'last', KSX[:cap][-1],
              'bytes', sum(map(len, pages)))
    return out


def patch_archive(raw, fonts):
    d, _, ents, _, _ = dave.read_dave_bytes(raw)
    names = davename.names_of(d)
    idx = {n: i for i, n in enumerate(names)}
    reps, new = {}, {}
    for e in ents:
        data = dave.entry_data(d, e)
        if data[:4] != b'\x0a\0\0\0': continue
        try: t = strtbl.parse(data)
        except Exception: continue
        hit = 0
        for lang in t['langs']:
            if lang is None: continue
            for x in lang[0]:
                if x['text'] in TARGETS:
                    font, text = TARGETS[x['text']]
                    if font and font not in fonts: continue
                    x['font'] = font or x['font']
                    x['text'] = text.format(last=fonts[x['font']][3]); hit += 1
        if hit: reps[e['idx']] = strtbl.build(t)
    for f, (src, desc, pages, _) in fonts.items():
        i = idx[f + '.fonttex']
        assert dave.entry_data(d, ents[i]) == src, 'font copy differs: ' + f
        reps[i] = desc
        n0 = len(fontb.parse(src)['pages'])
        new.update({'%s_%02d.tex' % (f, n0 + k): p for k, p in enumerate(pages)})
    return dave_patch.insert(dave_patch.patch(raw, reps), new)


def main(out, cfg):
    img = bytearray(open(SRC_ISO, 'rb').read())
    assert hashlib.sha1(img).hexdigest() == SRC_SHA1, 'source ISO mismatch'
    fonts = None
    for arc in ARCHIVES:
        _, lba, size = iso9660.find(img, arc)
        raw = bytes(img[lba * 2048: lba * 2048 + size])
        fonts = fonts or make_fonts(raw, cfg)
        print(arc, iso9660.replace(img, arc, patch_archive(raw, fonts)))
    iso9660.finalize(img)
    open(out, 'wb').write(img)


if __name__ == '__main__':
    a = sys.argv[2:] + [None] * 4
    main(sys.argv[1], dict(fonts=(a[0] or 'berrylium,damaged,regulatorcondensed').split(','),
                           page=int(a[1] or 256), bpp=int(a[2] or 4), maxnew=int(a[3] or 24)))
