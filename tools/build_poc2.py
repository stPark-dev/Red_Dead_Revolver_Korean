"""PoC2: EUC-KR pair -> hooked lookup -> '@' glyph slot redrawn as '가'. Builds from the immutable source ISO."""
import sys, os, hashlib, json, struct
NO_ELF = os.environ.get('NO_ELF'); NO_FONT = os.environ.get('NO_FONT')
sys.path.insert(0, 'tools'); sys.path.insert(0, 'hook')
import dave, dave_patch, strtbl, iso9660, fontbundle, poc2
from PIL import Image, ImageDraw, ImageFont

SRC_ISO = 'orig/Red Dead Revolver (USA).iso'
SRC_SHA1 = '7bbe502a1b170f80e378a566ad8ec313dba78361'
RAM_REF = 'work/dumps/ee_title.bin'
KFONT = '../fonts/NotoSerifKR-Bold.otf'
OUT = sys.argv[1]
TARGETS = json.load(open(sys.argv[2], encoding='utf-8'))
SIG = b'\x7e\x00\x7f\x00\x80\x00\x81\x00\x8d\x00'
GLYPH_CHAR = '가'

def render(ch, h):
    size = h
    for _ in range(40):
        f = ImageFont.truetype(KFONT, size)
        x0, y0, x1, y1 = f.getbbox(ch)
        if y1 - y0 <= h: break
        size -= 1
    w = x1 - x0
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((-x0, -y0 + (h - (y1 - y0)) // 2), ch, font=f, fill=255)
    return im

def free_spot(occ, W, H, w, h):
    for y in range(0, min(H - h, 255) + 1):
        for x in range(0, W - w + 1, 2):
            if all(not occ[yy][xx] for yy in range(max(0, y - 1), min(H, y + h + 1)) for xx in range(max(0, x - 1), min(W, x + w + 1))):
                return x, y
    return None

def patch_bundle(data):
    b = fontbundle.Bundle(data)
    n = 0
    for f in b.fonts():
        codes = f['codes']
        if 0x40 not in codes or 0x57 not in codes: continue
        at, wi = codes.index(0x40), codes.index(0x57)
        for v in f['variants']:
            gW = b.glyph(v, wi)
            if gW[3] == 0: continue
            W, H = v['W'], v['H']
            occ = [[False] * W for _ in range(H)]
            for i in range(f['n']):
                g = b.glyph(v, i)
                gx, gy = g[0] * 2, g[1]
                for yy in range(gy, min(H, gy + g[3])):
                    for xx in range(gx, min(W, gx + g[2])): occ[yy][xx] = True
            im = render(GLYPH_CHAR, gW[3])
            spot = free_spot(occ, W, H, im.width, im.height)
            assert spot, 'no free atlas space'
            px = b.read_t4(v)
            for yy in range(im.height):
                for xx in range(im.width):
                    px[(spot[1] + yy) * W + spot[0] + xx] = im.getpixel((xx, yy)) >> 4
            if os.environ.get('EDIT', 'pga').find('p') >= 0: b.write_t4(v, px)
            scale = (gW[6] - gW[4]) / gW[2]
            g = [spot[0] // 2, spot[1], im.width, im.height, gW[4], gW[5], gW[4] + round(im.width * scale), gW[7]]
            if 'g' in os.environ.get('EDIT', 'pga'): b.set_glyph(v, at, g)
            n += 1
        if 'a' in os.environ.get('EDIT', 'pga') and f['adv'] and b.contains(f['adv']):
            o = b.off(f['adv'])
            struct.pack_into('<H', b.d, o + 2 * at, struct.unpack_from('<H', b.d, o + 2 * wi)[0])
    return bytes(b.d), n

img = bytearray(open(SRC_ISO, 'rb').read())
assert hashlib.sha1(img).hexdigest() == SRC_SHA1, 'source ISO mismatch'
# 1) executable
_, lba, size = iso9660.find(img, 'SLUS_205.00')
elf = bytes(img[lba * 2048: lba * 2048 + size])
if not NO_ELF:
    newelf, *_ = poc2.patch_elf(elf, open(RAM_REF, 'rb').read())
    print('SLUS', iso9660.replace(img, 'SLUS_205.00', newelf))
# 2) archives
for arc in ['FRONT.DAT', 'SWAT.DAT']:
    _, lba, size = iso9660.find(img, arc)
    raw = bytes(img[lba * 2048: lba * 2048 + size])
    d, _, ents, _, _ = dave.read_dave_bytes(raw)
    reps = {}; nf = 0
    for e in ents:
        data = dave.entry_data(d, e)
        if data[:4] == b'\x0a\0\0\0':
            try: t = strtbl.parse(data)
            except Exception: t = None
            if t:
                hit = 0
                for lang in t['langs']:
                    if lang is None: continue
                    for x in lang[0]:
                        if x['text'] in TARGETS: x['text'] = TARGETS[x['text']]; hit += 1
                if hit: reps[e['idx']] = strtbl.build(t)
        elif SIG in data and not NO_FONT and (not os.environ.get('FONT_ARC') or os.environ['FONT_ARC'] == arc) and (not os.environ.get('FONT_IDX') or e['idx'] in json.loads(os.environ['FONT_IDX'])):
            nd, n = patch_bundle(data)
            if os.environ.get('NOEDIT'): nd = data
            if n: reps[e['idx']] = nd; nf += n
    print(arc, 'entries', len(reps), 'font variants', nf)
    print(arc, iso9660.replace(img, arc, dave_patch.patch(raw, reps)))
iso9660.finalize(img)
open(OUT, 'wb').write(img)
