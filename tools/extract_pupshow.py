"""Extract every cutscene subtitle file (lvl_*_pupshow_*_en.txt) into a translation baseline.

usage: extract_pupshow.py SOURCE.iso OUT.jsonl
One record per cue (see pupshow.records); src is the displayed text (quotes stripped, two lines joined
by '\\n', tokenized by textcodec). Copies of a file must be identical; reach is "game" if any copy
lives outside SWAT.DAT, else "swat-only".
"""
import sys, json, hashlib
sys.path.insert(0, 'tools')
import iso9660, dave, davename, pupshow, textcodec

SRC_SHA1 = '7bbe502a1b170f80e378a566ad8ec313dba78361'


def main(iso, out):
    img = open(iso, 'rb').read()
    if hashlib.sha1(img).hexdigest() != SRC_SHA1: raise SystemExit('source ISO SHA1 mismatch')
    files, copies = {}, {}
    for path, lba, size in iso9660.list_files(img):
        if not path.endswith('.DAT') or path == 'STREAMS.DAT': continue
        raw = img[lba * 2048: lba * 2048 + size]
        if raw[:4] != b'Dave': continue
        d, _, ents, _, _ = dave.read_dave_bytes(raw)
        for name, e in zip(davename.names_of(d), ents):
            if '_pupshow_' not in name or not name.endswith('_en.txt'): continue
            b = dave.entry_data(d, e)
            if files.setdefault(name, b) != b: raise ValueError('copies of %s differ' % name)
            copies.setdefault(name, []).append('%s#%d' % (path, e['idx']))
    recs = pupshow.records(files, copies)
    for r in recs:
        r['src'] = textcodec.to_tokens(r['src'])
        r['reach'] = 'game' if any(not c.startswith('SWAT.DAT#') for c in r['copies']) else 'swat-only'
    with open(out, 'w', encoding='utf-8') as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('%d files, %d cues (%d swat-only), %d chars' % (
        len(files), len(recs), sum(r['reach'] != 'game' for r in recs), sum(len(r['src']) for r in recs)))


if __name__ == '__main__':
    main(*sys.argv[1:])
