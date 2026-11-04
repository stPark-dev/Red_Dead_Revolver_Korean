"""Merge a translation batch {id: ko} into a translation file (default text/strtbl_ko.jsonl), then run the mechanical checks.

usage: tr_merge.py BATCH.json [--state needs_review] [--replace] [--baseline SRC.jsonl --out KO.jsonl]
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translation


ap = argparse.ArgumentParser()
ap.add_argument('batch'); ap.add_argument('--state', default='needs_review'); ap.add_argument('--replace', action='store_true')
ap.add_argument('--baseline', default='text/strtbl_src.jsonl'); ap.add_argument('--out', default='text/strtbl_ko.jsonl')
a = ap.parse_args()
BASELINE, OUT = a.baseline, a.out
src = {r['id']: r for r in translation.load_jsonl(BASELINE)}
recs = translation.load_jsonl(OUT) if os.path.exists(OUT) else []
new = json.load(open(a.batch, encoding='utf-8'))
merged = translation.merge(src, recs, new, a.state, replace=a.replace)
errs = translation.check(src, merged)
if errs:
    print('\n'.join(errs)); sys.exit(1)
with open(OUT, 'w', encoding='utf-8') as f:
    for r in merged: f.write(json.dumps(r, ensure_ascii=False) + '\n')
done = sum(1 for r in merged if 'ko' in r or 'same_as' in r)
print('merged %d; %d/%d entries have a translation' % (len(new), done, len(src)))
