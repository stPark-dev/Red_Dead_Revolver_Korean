"""Cutscene subtitle files `lvl_*_pupshow_*_<lang>.txt` (shown when Sound Options > Subtitles is on).

UTF-16LE with BOM, CRLF lines of `time<TAB>line1<TAB>line2<TAB>duration`. Fields holding a comma are
quoted spreadsheet-style; the game strips the quotes (checked in the opening cutscene). Some files end
with one stray byte, kept as-is. Rendered in berrylium.
Key-based level files (lvl_*_subtitles_en.txt) put a key line `key<TAB><TAB><TAB>` before the cues of
one utterance; key lines are kept verbatim and label the cues after them (cue_keys).
"""
import re

TIME = re.compile(r'\d+:\d+(\.\d+)?$')
BOM = b'\xff\xfe'
FONT = 'berrylium'


def parse(b):
    """{'lines': [cue dict | raw str], 'tail': bytes}. A cue is a 4-field line with a time;
    anything else (blank or whitespace-only junk lines some files end with) is kept verbatim."""
    if b[:2] != BOM: raise ValueError('not UTF-16LE with BOM')
    tail = b[-1:] if len(b) % 2 else b''
    lines = b[2:len(b) - len(tail)].decode('utf-16-le').split('\r\n')
    if lines[-1] != '': raise ValueError('missing final CRLF')
    out = []
    for line in lines[:-1]:
        f = line.split('\t')
        if len(f) >= 4 and TIME.match(f[0].strip()) and not any(x.strip() for x in f[4:]):
            out.append(dict(time=f[0], l1=f[1], l2=f[2], dur=f[3], rest=''.join('\t' + x for x in f[4:])))
        elif _key(line) or not line.strip():
            out.append(line)
        else:
            raise ValueError('unexpected line %r' % line)
    return dict(lines=out, tail=tail)


def _key(line):
    """The key of a key line (key, then three empty fields), else None."""
    f = line.split('\t')
    return f[0].strip() if len(f) >= 4 and f[0].strip() and not any(x.strip() for x in f[1:]) else None


def cue_keys(doc):
    """Key of each cue (the last key line before it), None in files without key lines."""
    out, key = [], None
    for x in doc['lines']:
        if isinstance(x, dict): out.append(key)
        else: key = _key(x) or key
    return out


def cues(doc):
    return [x for x in doc['lines'] if isinstance(x, dict)]


def build(doc):
    text = ''.join(('%s\t%s\t%s\t%s%s' % (x['time'], x['l1'], x['l2'], x['dur'], x.get('rest', ''))
                    if isinstance(x, dict) else x)
                   + '\r\n' for x in doc['lines'])
    return BOM + text.encode('utf-16-le') + doc['tail']


def _clean(field):
    s = field.strip()
    if len(s) >= 2 and s[0] == s[-1] == '"': s = s[1:-1]
    return s.strip()


def display(cue):
    """Text as the player sees it: one or two lines joined by '\\n'."""
    l1, l2 = _clean(cue['l1']), _clean(cue['l2'])
    return l1 + '\n' + l2 if l2 else l1


def with_text(doc, texts):
    """Copy of doc with cues {index: 'line1' or 'line1\\nline2'} replaced (unquoted)."""
    lines = [dict(x) if isinstance(x, dict) else x for x in doc['lines']]
    at = [n for n, x in enumerate(lines) if isinstance(x, dict)]
    for i, t in texts.items():
        parts = t.split('\n')
        if len(parts) > 2 or '\t' in t or '"' in t or '\r' in t:
            raise ValueError('cue %d: not representable as two subtitle lines: %r' % (i, t))
        c = lines[at[i]]
        c['l1'], c['l2'] = parts[0], parts[1] if len(parts) > 1 else ''
    return dict(lines=lines, tail=doc['tail'])


def line_width(line, widths, space):
    return sum(space if c == ' ' else widths.get(ord(c), 0) for c in line)


def too_wide(texts, widths, limit, space):
    """['id: line N width W > limit'] for every display line wider than limit."""
    errs = []
    for rid, t in texts.items():
        for n, line in enumerate(t.split('\n'), 1):
            w = line_width(line, widths, space)
            if w > limit: errs.append('%s: line %d width %d > %d' % (rid, n, w, limit))
    return errs


def records(files, copies):
    """Baseline records, one per cue, in the strtbl baseline shape (table = file name, key = cue index)."""
    out = []
    for name in sorted(files):
        doc = parse(files[name])
        for i, (c, k) in enumerate(zip(cues(doc), cue_keys(doc))):
            out.append(dict(id='pupshow/%s/%d' % (name, i), table=name, key=str(i), font=FONT, src=display(c),
                            time=c['time'], copies=copies[name], reach='game'))
            if k is not None: out[-1]['cue_key'] = k
    return out
