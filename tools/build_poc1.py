"""PoC1: probe UTF-16 -> 8-bit conversion by editing one strtbl string in every archive copy."""
import sys, hashlib
sys.path.insert(0, 'tools')
import dave, dave_patch, strtbl, iso9660

SRC_ISO = 'orig/Red Dead Revolver (USA).iso'
SRC_SHA1 = '7bbe502a1b170f80e378a566ad8ec313dba78361'
ARCHIVES = ['FRONT.DAT', 'SWAT.DAT']
OUT = sys.argv[1]
import json
TARGETS = json.load(open(sys.argv[2], encoding='utf-8'))

img = bytearray(open(SRC_ISO, 'rb').read())
assert hashlib.sha1(img).hexdigest() == SRC_SHA1, 'source ISO mismatch'
for arc in ARCHIVES:
    _, lba, size = iso9660.find(img, arc)
    raw = bytes(img[lba * 2048: lba * 2048 + size])
    d, _, ents, _, _ = dave.read_dave_bytes(raw)
    reps = {}
    for e in ents:
        if d[e['off']:e['off'] + 1] == b'' : continue
        data = dave.entry_data(d, e)
        if data[:4] != b'\x0a\0\0\0': continue
        try: t = strtbl.parse(data)
        except Exception: continue
        hit = 0
        for lang in t['langs']:
            if lang is None: continue
            for x in lang[0]:
                if x['text'] in TARGETS: x['text'] = TARGETS[x['text']]; hit += 1
        if hit: reps[e['idx']] = strtbl.build(t)
    print(arc, 'modified entries', sorted(reps))
    if reps:
        print(arc, iso9660.replace(img, arc, dave_patch.patch(raw, reps)))
iso9660.finalize(img)
open(OUT, 'wb').write(img)
