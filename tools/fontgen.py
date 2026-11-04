"""Pack extra glyphs (e.g. Hangul) into new font B texture pages.

The engine looks glyphs up by binary search over the code-sorted descriptor, so new codes
above the existing ones can be appended; each new page holds a fixed grid of equal cells.
"""
import fontb


def coverage_map(palette):
    """Palette index whose alpha is nearest to each coverage value 0..255 (lowest index wins ties)."""
    return [min(range(len(palette)), key=lambda i: (abs(palette[i][3] - v), i)) for v in range(256)]


def add_pages(desc, chars, cell, yoff, page, bpp, palette, render):
    """Return (new descriptor, [page bytes]) with `chars` drawn on new pages.

    cell=(w, h) glyph box, page=(w, h) texture size, render(ch, w, h) -> PIL 'L' image.
    """
    (cw, ch), (pw, ph) = cell, page
    if cw > pw or ch > ph or pw > 256 or ph > 256:
        raise ValueError('cell %s does not fit page %s (max 256)' % (cell, page))
    codes = sorted(set(map(ord, chars)))
    if desc['glyphs'] and codes and codes[0] <= desc['glyphs'][-1]['code']:
        raise ValueError('new codes must be above existing ones (U+%04X)' % codes[0])
    per_row, rows = pw // cw, ph // ch
    per_page = per_row * rows
    amap = coverage_map(palette)
    out, pages, pg = desc, [], None
    for i, code in enumerate(codes):
        slot = i % per_page
        if slot == 0:
            if pg: pages.append(fontb.build_page(pg))
            pg = fontb.blank_page(pw, ph, bpp, palette)
        x, y = (slot % per_row) * cw, (slot // per_row) * ch
        img = render(chr(code), cw, ch)
        for yy in range(ch):
            row = (y + yy) * pw + x
            for xx in range(cw):
                pg['pixels'][row + xx] = amap[img.getpixel((xx, yy))]
        out = fontb.add_glyph(out, dict(code=code, x=x, y=y, w=cw, h=ch, yoff=yoff), new_page=(slot == 0))
    if pg: pages.append(fontb.build_page(pg))
    return out, pages
