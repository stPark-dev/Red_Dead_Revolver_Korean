"""Layout (.swui) text population: fonts that render each string-table key, and literal texts.

usage: extract_layout.py SOURCE.iso OUT.json
Only layouts present in an archive other than SWAT.DAT are considered reachable.
"""
import sys, os, json, hashlib, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso9660, dave, davename, swui, translation

SRC_SHA1 = '7bbe502a1b170f80e378a566ad8ec313dba78361'


def scan(img):
    found = {}
    for path, lba, size in iso9660.list_files(img):
        if not path.endswith('.DAT') or path == 'STREAMS.DAT': continue
        raw = img[lba * 2048: lba * 2048 + size]
        d, magic, ents, _, _ = dave.read_dave_bytes(raw)
        if magic != b'Dave': continue
        for n, e in zip(davename.names_of(d), ents):
            if n.endswith('.swui'):
                b = dave.entry_data(d, e)
                rec = found.setdefault(n, {'variants': {}, 'archives': set()})
                rec['variants'][hashlib.md5(b).hexdigest()] = b.decode('latin1')
                rec['archives'].add(path)
    return found


def main(iso, out):
    img = open(iso, 'rb').read()
    if hashlib.sha1(img).hexdigest() != SRC_SHA1: raise SystemExit('source ISO SHA1 mismatch')
    # only tables loaded in game count as keys; lvl_frontend (SWAT-only) is not loaded: its 'Chapter N'
    # keys were left untouched on screen (QA 2026-11-03), so those layout refs are literals
    keys = {r['key'] for r in translation.load_jsonl('text/strtbl_src.jsonl') if r['reach'] == 'game'}
    lmap = json.load(open('text/layout_map.json'))
    key_fonts, literals = {}, {}
    for name, rec in sorted(scan(img).items()):
        if rec['archives'] <= {'SWAT.DAT'}: continue
        for text in rec['variants'].values():
            for ref, fonts in swui.ref_fonts(text, lmap.get(name, {})).items():
                fonts = sorted(f for f in fonts if f)
                target = key_fonts if ref in keys else literals
                ent = target.setdefault(ref, {'fonts': set(), 'files': set()})
                ent['fonts'].update(fonts); ent['files'].add(name)
    for pat, fonts in lmap.get('runtime', {}).items():
        for k in keys:
            if re.search(pat, k):
                ent = key_fonts.setdefault(k, {'fonts': set(), 'files': set()})
                ent['fonts'].update(fonts); ent['files'].add('runtime:' + pat)
    conv = lambda d: {k: {'fonts': sorted(v['fonts']), 'files': sorted(v['files'])} for k, v in sorted(d.items())}
    json.dump({'key_fonts': conv(key_fonts), 'literals': conv(literals)}, open(out, 'w'), indent=1)
    print(len(key_fonts), 'keys,', len(literals), 'literal refs')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
