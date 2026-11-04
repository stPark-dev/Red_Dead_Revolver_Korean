"""Angel-engine string table (RDR PS2): ELF-hashed keys, per-language UTF-16 entries."""
import struct, sys


def elf_hash(key):
    """Entry hash = classic ELF/PJW hash of the case-sensitive key (28-bit)."""
    h = 0
    for c in key.encode('latin1'):
        h = ((h << 4) + c) & 0xffffffff
        g = h & 0xf0000000
        if g: h ^= g >> 24
        h &= ~g & 0xffffffff
    return h


def entries_by_key(t, lang=0):
    """{key: entry} for one language; every entry hash must match exactly one key."""
    by_hash = {}
    for k in t['keys']:
        by_hash.setdefault(elf_hash(k), []).append(k)
    out = {}
    for e in t['langs'][lang][0]:
        ks = by_hash.get(e['hash'], [])
        if len(ks) != 1: raise ValueError('hash %#x matches keys %r' % (e['hash'], ks))
        out[ks[0]] = e
    return out

def parse(d):
    nlang = struct.unpack_from('<I', d, 0)[0]
    loffs = struct.unpack_from('<%dI' % nlang, d, 4)
    p = 4 + 4 * nlang
    nbuck, nkeys = struct.unpack_from('<II', d, p); p += 8; unk = None
    keys = []
    for _ in range(nkeys):
        n = struct.unpack_from('<I', d, p)[0]; p += 4
        keys.append(d[p:p+n].decode('latin1')); assert d[p+n] == 0; p += n + 1
    assert p == loffs[0], (hex(p), hex(loffs[0]))
    langs = []
    for li in range(nlang):
        p = loffs[li]
        if p >= len(d): langs.append(None); continue
        cnt = struct.unpack_from('<I', d, p)[0]; p += 4
        ents = []
        for _ in range(cnt):
            h, a, b = struct.unpack_from('<IBB', d, p); p += 6
            fl = struct.unpack_from('<I', d, p)[0]; p += 4
            font = d[p:p+fl].decode('latin1'); p += fl
            sl = struct.unpack_from('<I', d, p)[0]; p += 4
            s = d[p:p+2*sl].decode('utf-16le'); p += 2*sl
            assert s.endswith('\0'); s = s[:-1]
            sx, sy, tail = struct.unpack_from('<ffH', d, p); p += 10
            ents.append(dict(hash=h, a=a, b=b, font=font, text=s, sx=sx, sy=sy, tail=tail))
        langs.append((ents, p))
    return dict(nlang=nlang, loffs=loffs, nbuck=nbuck, unk=unk, keys=keys, langs=langs)

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    t = parse(d)
    e, end = t['langs'][0]
    print('keys', len(t['keys']), 'entries', len(e), 'end', hex(end), 'size', hex(len(d)), t['nbuck'], t['unk'])

def build(t):
    """Serialize parsed table (only language 0 populated, others empty)."""
    out = bytearray()
    nlang = t['nlang']
    out += struct.pack('<I', nlang) + b'\0' * (4 * nlang)
    out += struct.pack('<II', t['nbuck'], len(t['keys']))
    for k in t['keys']:
        kb = k.encode('latin1'); out += struct.pack('<I', len(kb)) + kb + b'\0'
    offs = []
    for li in range(nlang):
        lang = t['langs'][li]
        alias = [j for j in range(li) if 'loffs' in t and t['loffs'][j] == t['loffs'][li] and lang is not None]
        if alias:  # languages sharing one data block in the source stay shared
            offs.append(offs[alias[0]]); continue
        offs.append(len(out))
        if lang is None: continue
        ents = lang[0]
        out += struct.pack('<I', len(ents))
        for e in ents:
            fb = e['font'].encode('latin1')
            s = (e['text'] + '\0').encode('utf-16le')
            out += struct.pack('<IBB', e['hash'], e['a'], e['b'])
            out += struct.pack('<I', len(fb)) + fb
            out += struct.pack('<I', len(s) // 2) + s
            out += struct.pack('<ffH', e['sx'], e['sy'], e['tail'])
    end = len(out)
    offs = [o if t['langs'][i] is not None else end for i, o in enumerate(offs)]
    struct.pack_into('<%dI' % nlang, out, 4, *offs)
    return bytes(out)


def add_entries(t, new, lang=0):
    """Return a copy of t with {key: (font, text)} added (keys kept sorted; scale 1.0)."""
    import copy
    if set(new) & set(t['keys']): raise ValueError('keys exist: %s' % sorted(set(new) & set(t['keys'])))
    t2 = copy.deepcopy(t)
    t2['keys'] = sorted(t2['keys'] + list(new))
    ents, end = t2['langs'][lang]
    for k, (font, text) in new.items():
        ents.append(dict(hash=elf_hash(k), a=1, b=0, font=font, text=text, sx=1.0, sy=1.0, tail=0))
    t2['langs'][lang] = (ents, end)
    return t2
