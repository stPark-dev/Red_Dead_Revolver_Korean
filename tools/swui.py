"""Layout scripts (*.swui): which font renders which text reference.

<FONT:name[:SCALE..]> sets the current font for following <TEXT|TEXTBOX|READOUT:...:ref> elements (the
last ':'-field is the reference), <BUTTON|COMBO:x,y,z:label:...> and <COMBODATA:label:value>. A reference is: a string-table key, or a literal shown as-is when no key matches.
<LOOKUPDATA:a, b, ...> rows feed named elements; lookup_map tells which element each column fills.
"""
import re

ELEM = re.compile(r'<(TEXT|TEXTBOX|READOUT):([^>]*)>')
LABEL = re.compile(r'<(BUTTON|COMBO):[^:>]*:([^:>]*)[:>]')   # <BUTTON:x,y,z:label:...>
OPTION = re.compile(r'<COMBODATA:([^:>]*)[:>]')              # <COMBODATA:label:value>


def _lines(text):
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(';'): continue
        yield s.split(' ;')[0].split('\t;')[0]


def text_uses(text):
    """[(font, ref)] in file order; font names lower-cased."""
    font, out = None, []
    for s in _lines(text):
        m = re.match(r'<FONT:([^:>]+)', s)
        if m: font = m.group(1).lower(); continue
        for m in ELEM.finditer(s):
            out.append((font, m.group(2).split(':')[-1].strip()))
        for m in LABEL.finditer(s):
            out.append((font, m.group(2).strip()))
        for m in OPTION.finditer(s):
            out.append((font, m.group(1).strip()))
    return out


def lookup_rows(text):
    rows, cur = {}, None
    for s in _lines(text):
        m = re.match(r'<LOOKUP:([^>]+)>', s)
        if m: cur = m.group(1); rows.setdefault(cur, []); continue
        m = re.match(r'<LOOKUPDATA:([^>]*)>', s)
        if m and cur: rows[cur].append([x.strip() for x in m.group(1).split(',')])
    return rows


def ref_fonts(text, lookup_map=None):
    """{ref: {fonts}}; lookup cells go to their mapped element, or to every font of the file if unmapped."""
    out = {}
    elem_font = {}
    for font, ref in text_uses(text):
        out.setdefault(ref, set()).add(font)
        elem_font.setdefault(ref, set()).add(font)
    all_fonts = {f for fs in elem_font.values() for f in fs if f}
    for name, rows in lookup_rows(text).items():
        cols = (lookup_map or {}).get(name)
        for row in rows:
            if cols is None:  # unknown routing: any font of this layout may render the cell
                for cell in row: out.setdefault(cell, set()).update(all_fonts)
                continue
            for cell, elem in zip(row, cols):
                if elem and elem in elem_font: out.setdefault(cell, set()).update(elem_font[elem])
    return out
