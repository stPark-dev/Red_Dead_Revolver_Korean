"""Lone-word (orphan) audit for the HUD text boxes, which wrap greedily at spaces.

Box limits are unscaled berrylium advances measured in game (docs/survey.md, HUD word wrap):
top hint box 464..468, bottom letterbox box 567..571, both for strings drawn at sx 0.8.
A string is flagged when its Korean wrap leaves a last line under ORPHAN_RATIO of the box at some limit
while the English source does not.

usage: wrap_audit.py [KO.jsonl]   (needs the extracted work/iso/FRONT.DAT for the font metrics)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textcodec

LIMITS = (464, 468, 567, 571)
SX = 0.8
ORPHAN_RATIO = 0.2
HANGUL_W = {'berrylium': 22}  # Korean glyph advance = cell width (build_patch.FONTS)


def width(text, widths, space, tracking):
    """Unscaled advance; characters without a glyph count as 0 (the game drops them; the build rejects them in Korean)."""
    return sum(space if c == ' ' else (widths[ord(c)] + tracking if ord(c) in widths else 0) for c in text)


def wrap(text, limit, widths, space, tracking):
    out = []
    for para in text.split('\n'):
        cur = ''
        for word in para.split(' '):
            t = cur + ' ' + word if cur else word
            if cur and width(t, widths, space, tracking) > limit:
                out.append(cur); cur = word
            else:
                cur = t
        out.append(cur)
    return out


def orphan(text, limit, widths, space, tracking):
    """True when wrapping (not an explicit newline) leaves a short last line in the last paragraph."""
    lines = wrap(text.split('\n')[-1], limit, widths, space, tracking)
    return len(lines) > 1 and width(lines[-1], widths, space, tracking) < ORPHAN_RATIO * limit


def audit(src_by_id, recs, metrics, limits=LIMITS):
    """[{id, limit, lines}] for Korean-introduced orphans; metrics: {font: dict(widths, space, tracking)}."""
    hits = []
    for r in recs:
        s = src_by_id.get(r['id'])
        if not r.get('ko') or not s or s['font'] not in metrics or abs(s['sx'] - SX) > 1e-3: continue
        m = metrics[s['font']]
        ko, en = textcodec.from_tokens(r['ko']).strip(), textcodec.from_tokens(s['src']).strip()
        for lim in limits:
            if orphan(ko, lim, **m) and not orphan(en, lim, **m):
                hits.append(dict(id=r['id'], limit=lim, lines=wrap(ko, lim, **m))); break
    return hits


def game_metrics(front_dat='work/iso/FRONT.DAT'):
    import dave, davename, fontb
    d, _, ents, _, _ = dave.read_dave(front_dat)
    names = davename.names_of(d)
    out = {}
    for f, hw in HANGUL_W.items():
        src = dave.entry_data(d, ents[names.index(f + '.fonttex')])
        widths = {g['code']: g['w'] for g in fontb.parse(src)['glyphs']}
        widths.update({c: hw for c in range(0xAC00, 0xD7A4)})
        out[f] = dict(widths=widths, tracking=int.from_bytes(src[8:12], 'little'),
                      space=int.from_bytes(src[12:16], 'little'))
    return out


if __name__ == '__main__':
    ko_path = sys.argv[1] if len(sys.argv) > 1 else 'text/strtbl_ko.jsonl'
    src = {json.loads(l)['id']: json.loads(l) for l in open('text/strtbl_src.jsonl', encoding='utf-8')}
    recs = [json.loads(l) for l in open(ko_path, encoding='utf-8')]
    hits = audit(src, recs, game_metrics())
    for h in hits: print('%s\t%d\t%s' % (h['id'], h['limit'], ' | '.join(h['lines'])))
    print('%d orphan candidates' % len(hits), file=sys.stderr)
