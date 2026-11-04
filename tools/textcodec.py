"""Reversible text form for translation: icon glyphs as {TOKENS}, literal braces doubled.

Icon glyphs in font B (controller buttons, verified by rendering the glyph bitmaps):
U+00BA/BC/BD/BE are round face-button icons, U+2020-2023 are wide bar icons.
"""
import re

ICONS = {'º': 'BTN_BA', '¼': 'BTN_BC', '½': 'BTN_BD', '¾': 'BTN_BE',
         '†': 'ICON_2020', '‡': 'ICON_2021', '•': 'ICON_2022', '‣': 'ICON_2023'}
BY_NAME = {v: k for k, v in ICONS.items()}
_TOKEN = re.compile(r'\{\{|\}\}|\{([A-Z0-9_]+)\}|[{}]')


def to_tokens(raw):
    out = []
    for c in raw:
        if c in ICONS: out.append('{%s}' % ICONS[c])
        elif c in '{}': out.append(c * 2)
        else: out.append(c)
    return ''.join(out)


def _scan(s):
    pos, parts, toks = 0, [], []
    for m in _TOKEN.finditer(s):
        parts.append(s[pos:m.start()]); pos = m.end()
        t = m.group(0)
        if t in ('{{', '}}'): parts.append(t[0])
        elif m.group(1) in BY_NAME: parts.append(BY_NAME[m.group(1)]); toks.append(m.group(1))
        else: raise ValueError('bad token %r at %d in %r' % (t, m.start(), s))
    parts.append(s[pos:])
    return ''.join(parts), toks


def from_tokens(s):
    return _scan(s)[0]


def tokens_of(s):
    return _scan(s)[1]
