"""Review sheets for translation review (GPT or human): TSV chunks of id / English / Korean.

Sheets cover string tables (one sheet set per table), cutscene/movie subtitles ('pupshow', in cue order),
layout literals ('layout') and text redrawn in images ('gfx', one row per label).
Newlines are written as a literal \\n; {TOKENS} are button icons and must be kept.
Edited sheets are applied with tools/review_apply.py.

usage: review_export.py OUTDIR [--size 150]
       review_export.py --import SHEET.tsv > batch.json
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HEADER = ('id', 'en', 'ko')


def _esc(s): return s.replace('\\', '\\\\').replace('\t', ' ').replace('\n', '\\n')


def _unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append({'n': '\n', '\\': '\\'}.get(s[i + 1], '\\' + s[i + 1])); i += 2
        else:
            out.append(s[i]); i += 1
    return ''.join(out)


def rows(src_by_id, recs):
    """One row per record that has its own Korean text (same_as copies follow their target)."""
    return [dict(id=r['id'], table=src_by_id[r['id']]['table'], en=_esc(src_by_id[r['id']]['src']), ko=_esc(r['ko']))
            for r in recs if r.get('ko') and r['id'] in src_by_id]


def _cue_order(rid):
    head, _, key = rid.rpartition('/')
    return (head, int(key)) if key.isdigit() else (head, -1, key)


def pup_rows(src_by_id, recs):
    """Subtitle rows in one 'pupshow' table, ordered by scene file and cue number (dialogue order)."""
    rs = [dict(r, table='pupshow') for r in rows(src_by_id, recs)]
    return sorted(rs, key=lambda r: _cue_order(r['id']))


def layout_rows(lt):
    return [dict(id='layout/' + lit, table='layout', en=_esc(lit), ko=_esc(e['ko']))
            for lit, e in sorted(lt['entries'].items()) if e.get('ko')]


def gfx_rows(spec):
    return [dict(id='gfx/%s/%d' % (name, i), table='gfx', en=_esc(it['en']), ko=_esc('\n'.join(it['lines'])))
            for name, img in spec['images'].items() for i, it in enumerate(img['items'])]


def chunks(rs, size=150):
    out, by_table = [], {}
    for r in rs: by_table.setdefault(r['table'], []).append(r)
    for t, rr in by_table.items():
        for i in range(0, len(rr), size):
            out.append(('%s-%02d' % (t, i // size + 1), rr[i:i + size]))
    return out


def to_tsv(rs):
    return '\n'.join(['\t'.join(HEADER)] + ['\t'.join(r[k] for k in HEADER) for r in rs]) + '\n'


def from_tsv_rows(text):
    """[(id, en as written in the sheet, ko unescaped)]."""
    lines = [l for l in text.splitlines() if l.strip()]
    if tuple(lines[0].split('\t')) != HEADER: raise ValueError('header must be: ' + '\t'.join(HEADER))
    out = []
    for n, l in enumerate(lines[1:], 2):
        f = l.split('\t')
        if len(f) != 3: raise ValueError('line %d: expected 3 tab-separated fields, got %d' % (n, len(f)))
        out.append((f[0], f[1], _unesc(f[2])))
    return out


def from_tsv(text):
    return {rid: ko for rid, _, ko in from_tsv_rows(text)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?'); ap.add_argument('--size', type=int, default=150); ap.add_argument('--import', dest='imp')
    a = ap.parse_args()
    if a.imp:
        json.dump(from_tsv(open(a.imp, encoding='utf-8').read()), sys.stdout, ensure_ascii=False, indent=1); sys.exit()
    src = {json.loads(l)['id']: json.loads(l) for l in open('text/strtbl_src.jsonl', encoding='utf-8')}
    recs = [json.loads(l) for l in open('text/strtbl_ko.jsonl', encoding='utf-8')]
    pup_src = {json.loads(l)['id']: json.loads(l) for l in open('text/pupshow_src.jsonl', encoding='utf-8')}
    pup_recs = [json.loads(l) for l in open('text/pupshow_ko.jsonl', encoding='utf-8')]
    rs = (rows(src, recs) + pup_rows(pup_src, pup_recs) + layout_rows(json.load(open('text/layout_ko.json', encoding='utf-8')))
          + gfx_rows(json.load(open('text/gfx_ko.json', encoding='utf-8'))))
    os.makedirs(a.out, exist_ok=True)
    cs = chunks(rs, a.size)
    for name, rr in cs:
        open(os.path.join(a.out, name + '.tsv'), 'w', encoding='utf-8').write(to_tsv(rr))
    print('%d sheets, %d rows -> %s' % (len(cs), sum(len(r) for _, r in cs), a.out))
