"""Apply edited review sheets (tools/review_export.py) to the translation files.

Rows are routed by id: 'pupshow/...' -> text/pupshow_ko.jsonl, 'layout/<literal>' -> text/layout_ko.json,
'gfx/<image>/<item>' -> text/gfx_ko.json, anything else -> text/strtbl_ko.jsonl.
Only rows whose Korean differs from the current translation are applied; they become needs_review
(an image becomes needs_review when any of its labels changes). Unchanged rows keep their state.
A sheet re-saved with CSV quoting is read back (unquote_csv).
Nothing is written if any row fails: unknown id, edited/shifted English column, token or glyph errors.

usage: review_apply.py SHEET.tsv [SHEET.tsv ...] [--dry-run]
"""
import sys, os, json, copy, csv, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translation, review_export as rx

STATE = 'needs_review'
PATHS = dict(strtbl=('text/strtbl_src.jsonl', 'text/strtbl_ko.jsonl'), pupshow=('text/pupshow_src.jsonl', 'text/pupshow_ko.jsonl'),
             layout='text/layout_ko.json', gfx='text/gfx_ko.json')


def route(rows):
    out = dict(pupshow={}, layout={}, gfx={}, strtbl={})
    for rid, _, ko in rows:
        if rid.startswith('pupshow/'): out['pupshow'][rid] = ko
        elif rid.startswith('layout/'): out['layout'][rid[len('layout/'):]] = ko
        elif rid.startswith('gfx/'): out['gfx'][rid[len('gfx/'):]] = ko
        else: out['strtbl'][rid] = ko
    return out


def _csv_cell(s):
    """What a CSV-aware tool (tab-delimited) reads from a raw sheet cell."""
    return next(csv.reader([s], delimiter='\t'))[0] if s else s


def unquote_csv(rows, en_by_id):
    """Undo a CSV round trip (GPT/spreadsheet re-save): a row whose English column is not the raw source but
    reads back to what a CSV reader made of the source gets the source English and its Korean cell CSV-read."""
    out = []
    for rid, en, ko in rows:
        src = rx._esc(en_by_id[rid]) if rid in en_by_id else None
        if src is not None and en != src and _csv_cell(en) == _csv_cell(src):
            en, ko = src, rx._unesc(_csv_cell(rx._esc(ko)))   # ko arrives unescaped
        out.append((rid, en, ko))
    return out


def english_mismatch(rows, en_by_id):
    """Rows whose English column is not the source of their id (edited, or rows shifted against ids)."""
    errs = []
    for rid, en, _ in rows:
        if rid not in en_by_id: errs.append('%s: unknown id' % rid)
        elif rx._esc(en_by_id[rid]) != en: errs.append('%s: English column differs from the source (row shifted or edited?)' % rid)
    return errs


def apply_jsonl(src_by_id, recs, new):
    """(merged records, changed count, errors) for a jsonl translation file."""
    cur = {r['id']: r for r in recs}

    def ko_of(rid):
        r = cur.get(rid, {})
        return cur.get(r['same_as'], {}).get('ko') if 'same_as' in r else r.get('ko')

    changed = {rid: ko for rid, ko in new.items() if ko_of(rid) != ko}
    errs = ['%s: unknown id' % rid for rid in changed if rid not in src_by_id]
    if errs: return recs, 0, errs
    merged = translation.merge(src_by_id, recs, changed, STATE, replace=True)
    return merged, len(changed), translation.check(src_by_id, merged)


def apply_layout(lt, new):
    out = copy.deepcopy(lt); n = 0; errs = []
    for lit, ko in new.items():
        ent = out['entries'].get(lit)
        if ent is None: errs.append('layout/%s: unknown literal' % lit); continue
        if ent.get('ko') == ko: continue
        errs += translation._ko_errors('layout/' + lit, lit, ko)
        out['entries'][lit] = dict(ent, ko=ko, state=STATE); n += 1
    return out, n, errs


def apply_gfx(spec, new):
    out = copy.deepcopy(spec); n = 0; errs = []
    for key, ko in new.items():
        name, _, idx = key.rpartition('/')
        img = out['images'].get(name)
        if img is None or not idx.isdigit() or int(idx) >= len(img['items']):
            errs.append('gfx/%s: unknown image label' % key); continue
        lines = ko.split('\n')
        if img['items'][int(idx)]['lines'] == lines: continue
        img['items'][int(idx)]['lines'] = lines; img['state'] = STATE; n += 1
    return out, n, errs


def _jsonl_src(kind):
    return {r['id']: r for r in translation.load_jsonl(PATHS[kind][0])}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('sheets', nargs='+'); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    rows = [r for s in a.sheets for r in rx.from_tsv_rows(open(s, encoding='utf-8').read())]
    srcs = {k: _jsonl_src(k) for k in ('strtbl', 'pupshow')}
    lt = json.load(open(PATHS['layout'], encoding='utf-8')); spec = json.load(open(PATHS['gfx'], encoding='utf-8'))
    en = {rid: r['src'] for k in srcs for rid, r in srcs[k].items()}
    en.update({'layout/' + lit: lit for lit in lt['entries']})
    en.update({'gfx/%s/%d' % (n, i): it['en'] for n, img in spec['images'].items() for i, it in enumerate(img['items'])})
    rows = unquote_csv(rows, en); by = route(rows)
    errs = english_mismatch(rows, en)
    results = {}
    for k in ('strtbl', 'pupshow'):
        if by[k]:
            results[k] = apply_jsonl(srcs[k], translation.load_jsonl(PATHS[k][1]), by[k]); errs += results[k][2]
    if by['layout']: results['layout'] = apply_layout(lt, by['layout']); errs += results['layout'][2]
    if by['gfx']: results['gfx'] = apply_gfx(spec, by['gfx']); errs += results['gfx'][2]
    if errs:
        print('\n'.join(errs)); print('nothing written (%d errors)' % len(errs)); return 1
    for k, (data, n, _) in results.items():
        print('%s: %d of %d rows changed' % (k, n, len(by[k])))
        if a.dry_run or not n: continue
        path = PATHS[k][1] if k in srcs else PATHS[k]
        with open(path, 'w', encoding='utf-8') as f:
            if k in srcs: f.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in data)
            else: f.write(json.dumps(data, ensure_ascii=False, indent=1))  # same layout as the checked-in files
    return 0


if __name__ == '__main__':
    sys.exit(main())
