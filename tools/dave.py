"""Dave/DAVE archive reader (Angel engine, Red Dead Revolver PS2)."""
import struct, zlib, sys, os

def read_dave(path):
    return read_dave_bytes(open(path, 'rb').read())

def read_dave_bytes(d):
    magic = d[:4]
    n, ts, ns = struct.unpack_from('<III', d, 4)
    ents = []
    for i in range(n):
        no, off, us, cs = struct.unpack_from('<IIII', d, 0x800 + 16 * i)
        ents.append(dict(idx=i, nameoff=no, off=off, usize=us, csize=cs))
    return d, magic, ents, ts, ns

def entry_data(d, e):
    raw = d[e['off']:e['off'] + e['csize']]
    if e['usize'] == e['csize']:
        return raw
    out = zlib.decompress(raw, -15)
    assert len(out) == e['usize']
    return out

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    d, magic, ents, ts, ns = read_dave(src)
    os.makedirs(dst, exist_ok=True)
    for e in ents:
        open(os.path.join(dst, '%04d.bin' % e['idx']), 'wb').write(entry_data(d, e))
    print(magic, len(ents))
