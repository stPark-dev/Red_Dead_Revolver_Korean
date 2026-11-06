"""Translation records for the strtbl baseline: mechanical checks and product-build selection.

Record: {id, src (copy of the baseline at translation time), ko | same_as, state, note?}.
'src'/'id' are protected; only ko/same_as/state/note are authored.
"""
import json
from collections import Counter
import textcodec

STATES = ('untranslated', 'in_progress', 'needs_review', 'needs_human_review', 'distribution_eligible')
BETA_STATES = ('needs_review', 'needs_human_review', 'distribution_eligible')  # finished drafts may ship as a beta
NO_GLYPH = {'…': '...', '–': '-'}  # absent from every game font (dropped by the original)


def load_jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def _ko_errors(rid, src, ko):
    errs = []
    try:
        got = sorted(textcodec.tokens_of(ko))
    except ValueError as ex:
        return ['%s: %s' % (rid, ex)]
    if got != sorted(textcodec.tokens_of(src)):
        errs.append('%s: token set differs (%s vs %s)' % (rid, got, sorted(textcodec.tokens_of(src))))
    for c in set(ko) & set(NO_GLYPH):
        errs.append('%s: U+%04X has no glyph, use %r' % (rid, ord(c), NO_GLYPH[c]))
    return errs


def check(src_by_id, recs):
    errs, seen = [], Counter(r['id'] for r in recs)
    by_id = {r['id']: r for r in recs}
    for r in recs:
        rid = r['id']
        if rid not in src_by_id:
            errs.append('%s: unknown id' % rid); continue
        base = src_by_id[rid]
        if seen[rid] > 1: errs.append('%s: duplicate record' % rid)
        if r.get('src') != base['src']: errs.append('%s: source changed since translation' % rid)
        if r.get('state') not in STATES: errs.append('%s: bad state %r' % (rid, r.get('state')))
        if 'same_as' in r:
            t = by_id.get(r['same_as'])
            if t is None or 'ko' not in t or t['id'] not in src_by_id:
                errs.append('%s: same_as target %s missing' % (rid, r['same_as']))
            elif (src_by_id[t['id']]['src'], src_by_id[t['id']]['font']) != (base['src'], base['font']):
                errs.append('%s: same_as target %s has different source/font' % (rid, t['id']))
        elif r.get('ko') is not None:
            errs += _ko_errors(rid, base['src'], r['ko'])
    return errs


def select(src_by_id, recs, policy):
    """{id: raw text for the build}. dev: translation if present else source.
    beta: like dev, but every translation must be a finished draft (BETA_STATES). release: all eligible."""
    if policy not in ('dev', 'beta', 'release'): raise ValueError(policy)
    errs = check(src_by_id, recs)
    if errs: raise ValueError('translation check failed:\n' + '\n'.join(errs[:20]))
    if policy == 'beta':
        unready = [r['id'] for r in recs if r['state'] not in BETA_STATES and ('ko' in r or 'same_as' in r)]
        if unready: raise ValueError('%d translations not ready for beta, e.g. %s' % (len(unready), unready[:5]))
    by_id = {r['id']: r for r in recs}

    def ko_of(r):
        return by_id[r['same_as']]['ko'] if 'same_as' in r else r.get('ko')

    out, missing = {}, []
    for rid, base in src_by_id.items():
        r = by_id.get(rid)
        ko = ko_of(r) if r else None
        if policy == 'release' and (r is None or r['state'] != 'distribution_eligible' or ko is None):
            missing.append(rid); continue
        out[rid] = textcodec.from_tokens(ko if ko is not None else base['src'])
    if missing: raise ValueError('%d entries not distribution_eligible, e.g. %s' % (len(missing), missing[:5]))
    return out


def merge(src_by_id, recs, new, state, replace=False):
    """Add translations {id: ko}; every other baseline id with the same (font, src) gets same_as.

    Existing translations are kept unless replace=True (no silent last-writer-wins).
    """
    by_id = {r['id']: dict(r) for r in recs}
    for rid, ko in new.items():
        if rid not in src_by_id: raise ValueError('unknown id ' + rid)
        old = by_id.get(rid)
        if old is not None and 'ko' in old and old['ko'] != ko and not replace:
            raise ValueError('%s already translated; pass replace=True' % rid)
        by_id[rid] = dict(id=rid, src=src_by_id[rid]['src'], ko=ko, state=state)
        sig = (src_by_id[rid]['font'], src_by_id[rid]['src'])
        for oid, o in src_by_id.items():
            if oid != rid and (o['font'], o['src']) == sig and 'ko' not in by_id.get(oid, {}):
                by_id[oid] = dict(id=oid, src=o['src'], same_as=rid, state=state)
    return [by_id[k] for k in sorted(by_id)]
