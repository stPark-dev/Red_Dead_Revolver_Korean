"""Extract every string table on the disc into the translation source baseline.

usage: extract_strtbl.py SOURCE.iso OUT.jsonl
One record per (table, key): id, table, key, font, sx, sy, src (tokenized, see textcodec), copies
("ARCHIVE#entry"), reach ("game" if any copy lives outside SWAT.DAT, else "swat-only").
Backup/Xbox tables found only in SWAT.DAT are excluded and listed in OUT.excluded.json.
"""
import sys, json, hashlib, re
sys.path.insert(0, 'tools')
import iso9660, dave, davename, strtbl, textcodec

SRC_SHA1 = '7bbe502a1b170f80e378a566ad8ec313dba78361'
EXCLUDE = re.compile(r'^(backup_|bak2_|xb_)|_xbx\.|\.bak\.|_crap\.')


def collect(found):
    """found: [(archive, entry_idx, table_name, parsed_table)] -> (entries, excluded)."""
    recs, excluded = {}, []
    for arc, idx, name, t in found:
        where = '%s#%d' % (arc, idx)
        if EXCLUDE.search(name):
            excluded.append(dict(table=name, copy=where)); continue
        for key, e in strtbl.entries_by_key(t).items():
            rid = '%s/%s' % (name, key)
            src = dict(font=e['font'], sx=e['sx'], sy=e['sy'], src=textcodec.to_tokens(e['text']))
            r = recs.get(rid)
            if r is None:
                recs[rid] = r = dict(id=rid, table=name, key=key, **src, copies=[])
            elif any(r[k] != v for k, v in src.items()):
                raise ValueError('copies of %s differ: %s vs %s' % (rid, r['copies'][0], where))
            r['copies'].append(where)
    for r in recs.values():
        r['reach'] = 'game' if any(not c.startswith('SWAT.DAT#') for c in r['copies']) else 'swat-only'
    return [recs[k] for k in sorted(recs)], excluded


def scan(img):
    found = []
    for path, lba, size in iso9660.list_files(img):
        if not path.endswith('.DAT') or path == 'STREAMS.DAT': continue
        raw = bytes(img[lba * 2048: lba * 2048 + size])
        d, magic, ents, _, _ = dave.read_dave_bytes(raw)
        if magic != b'Dave': continue
        for name, e in zip(davename.names_of(d), ents):
            if name.endswith('.strtbl'):
                found.append((path, e['idx'], name, strtbl.parse(dave.entry_data(d, e))))
    return found


def main(iso, out):
    img = open(iso, 'rb').read()
    if hashlib.sha1(img).hexdigest() != SRC_SHA1: raise SystemExit('source ISO SHA1 mismatch')
    ents, excluded = collect(scan(img))
    with open(out, 'w', encoding='utf-8') as f:
        for r in ents: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    json.dump(excluded, open(out.rsplit('.', 1)[0] + '.excluded.json', 'w'), indent=1)
    print(len(ents), 'entries,', len(excluded), 'excluded copies')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
