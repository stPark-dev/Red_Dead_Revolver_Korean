"""Redraw text baked into IPU images in Korean (spec: text/gfx_ko.json).

Per item: inside `box` (x0, y0, x1, y1) the source text pixels (`mask`: 'dark' = luminance < 120,
'dark_gray' = also not reddish, so red leader lines survive; 'all' = the whole box) are dilated, inpainted (OpenCV Telea),
then `lines` are drawn at (x, y) aligned l/c/r in `color` and `font` (keys of the spec's colors/fonts),
`pitch` px apart (default size + LINE_GAP). Drawn text must stay inside the box.
Only macroblocks touching a box are re-encoded (ipu.replace_region); all others keep their bits.
"""
import hashlib
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import ipu

DARK = 120
RED_MARGIN = 30
LINE_GAP = 3
INPAINT_RADIUS = 6
MASKS = ('dark', 'dark_gray', 'all')
ALIGNS = ('l', 'c', 'r')


def text_mask(rgb, box, mode):
    """Bool mask (full frame) of source-text pixels inside box."""
    if mode not in MASKS: raise ValueError('unknown mask %r' % mode)
    x0, y0, x1, y1 = box
    out = np.zeros(rgb.shape[:2], bool)
    if mode == 'all':
        out[y0:y1, x0:x1] = True
        return out
    px = rgb[y0:y1, x0:x1].astype(int)
    m = (px @ np.array([299, 587, 114])) < DARK * 1000
    if mode == 'dark_gray': m &= (px[..., 0] - px[..., 2]) < RED_MARGIN
    out[y0:y1, x0:x1] = m
    return out


def _check(item, fonts, colors, w, h):
    x0, y0, x1, y1 = item['box']
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h): raise ValueError('bad box %r' % item['box'])
    if item['align'] not in ALIGNS: raise ValueError('bad align %r' % item['align'])
    if not item['lines'] or not all(item['lines']): raise ValueError('empty lines for %r' % item['en'])
    if item['color'] not in colors: raise ValueError('unknown color %r' % item['color'])
    if item['mask'] not in MASKS: raise ValueError('unknown mask %r' % item['mask'])
    if item['font'] not in fonts: raise ValueError('unknown font %r' % item['font'])


def _layout(item, font):
    """[(line, x, y)] and the ink bbox of all lines."""
    ft = ImageFont.truetype(font, item['size'])
    out, y = [], item['y']
    bx0 = by0 = 10 ** 9; bx1 = by1 = -10 ** 9
    for ln in item['lines']:
        l, t, r, b = ft.getbbox(ln)
        w = r - l
        x = {'l': item['x'], 'c': item['x'] - w // 2, 'r': item['x'] - w}[item['align']]
        out.append((ln, x - l, y - t))
        bx0, by0, bx1, by1 = min(bx0, x), min(by0, y), max(bx1, x + w), max(by1, y + b - t)
        y += item.get('pitch', item['size'] + LINE_GAP)
    return ft, out, (bx0, by0, bx1, by1)


def render(rgb, items, fonts, colors):
    h, w = rgb.shape[:2]
    mask = np.zeros((h, w), bool)
    inbox = np.zeros((h, w), bool)
    for it in items:
        _check(it, fonts, colors, w, h)
        mask |= text_mask(rgb, it['box'], it['mask'])
        x0, y0, x1, y1 = it['box']; inbox[y0:y1, x0:x1] = True
    mask = cv2.dilate(mask.astype(np.uint8) * 255, np.ones((3, 3), np.uint8), iterations=2) > 0
    mask &= inbox
    clean = cv2.inpaint(np.ascontiguousarray(rgb[..., ::-1]), mask.astype(np.uint8) * 255, INPAINT_RADIUS,
                        cv2.INPAINT_TELEA)[..., ::-1]
    im = Image.fromarray(np.ascontiguousarray(clean))
    dr = ImageDraw.Draw(im)
    for it in items:
        ft, lines, (bx0, by0, bx1, by1) = _layout(it, fonts[it['font']])
        x0, y0, x1, y1 = it['box']
        if bx0 < x0 or by0 < y0 or bx1 > x1 or by1 > y1:
            raise ValueError('text %r outside its box: ink %r box %r' % (it['lines'], (bx0, by0, bx1, by1), it['box']))
        for ln, x, y in lines:
            dr.text((x, y), ln, fill=tuple(colors[it['color']]), font=ft)
    return np.asarray(im)


def apply(src, spec, fonts, colors):
    """New IPU bytes for one image spec {src_sha1, q, items}."""
    if hashlib.sha1(src).hexdigest() != spec['src_sha1']: raise ValueError('source image differs from spec')
    doc = ipu.parse(src)
    new = render(ipu.decode(doc), spec['items'], fonts, colors)
    for it in spec['items']:
        doc = ipu.replace_region(doc, new, tuple(it['box']), q=spec['q'])
    return ipu.build(doc)
