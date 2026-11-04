"""Review sheets for translation review (GPT or human): TSV chunks of id / English / Korean per string table.

Newlines are written as a literal \\n; {TOKENS} are button icons and must be kept.
Edited sheets are read back with --import (from_tsv) and merged with tr_merge.py --replace.

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


def chunks(rs, size=150):
    out, by_table = [], {}
    for r in rs: by_table.setdefault(r['table'], []).append(r)
    for t, rr in by_table.items():
        for i in range(0, len(rr), size):
            out.append(('%s-%02d' % (t, i // size + 1), rr[i:i + size]))
    return out


def to_tsv(rs):
    return '\n'.join(['\t'.join(HEADER)] + ['\t'.join(r[k] for k in HEADER) for r in rs]) + '\n'


def from_tsv(text):
    lines = [l for l in text.splitlines() if l.strip()]
    if tuple(lines[0].split('\t')) != HEADER: raise ValueError('header must be: ' + '\t'.join(HEADER))
    out = {}
    for n, l in enumerate(lines[1:], 2):
        f = l.split('\t')
        if len(f) != 3: raise ValueError('line %d: expected 3 tab-separated fields, got %d' % (n, len(f)))
        out[f[0]] = _unesc(f[2])
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?'); ap.add_argument('--size', type=int, default=150); ap.add_argument('--import', dest='imp')
    a = ap.parse_args()
    if a.imp:
        json.dump(from_tsv(open(a.imp, encoding='utf-8').read()), sys.stdout, ensure_ascii=False, indent=1); sys.exit()
    src = {json.loads(l)['id']: json.loads(l) for l in open('text/strtbl_src.jsonl', encoding='utf-8')}
    recs = [json.loads(l) for l in open('text/strtbl_ko.jsonl', encoding='utf-8')]
    os.makedirs(a.out, exist_ok=True)
    cs = chunks(rows(src, recs), a.size)
    for name, rr in cs:
        open(os.path.join(a.out, name + '.tsv'), 'w', encoding='utf-8').write(to_tsv(rr))
    print('%d sheets, %d rows -> %s' % (len(cs), sum(len(r) for _, r in cs), a.out))
