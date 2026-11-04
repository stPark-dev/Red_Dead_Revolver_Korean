"""Replace entries in a Dave archive by appending new data (originals untouched)."""
import struct, zlib
from dave import read_dave

ALIGN = 0x800

def deflate_raw(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()

def patch(src_bytes, replacements, compress=True):
    """replacements: {entry_index: new_bytes}. Returns new archive bytes."""
    out = bytearray(src_bytes)
    n = struct.unpack_from('<I', out, 4)[0]
    for idx in sorted(replacements):
        if not 0 <= idx < n:
            raise ValueError('bad entry index %d' % idx)
        data = replacements[idx]
        packed = deflate_raw(data) if compress else data
        if compress and len(packed) >= len(data):
            packed = data  # stored
        pad = (-len(out)) % ALIGN
        out += b'\0' * pad
        off = len(out)
        out += packed
        no = struct.unpack_from('<I', out, 0x800 + 16 * idx)[0]
        struct.pack_into('<IIII', out, 0x800 + 16 * idx, no, off, len(data), len(packed))
    out += b'\0' * ((-len(out)) % ALIGN)
    return bytes(out)


def insert(src_bytes, new_entries, compress=True):
    """Add {name: bytes} entries, keeping the name-sorted TOC that lookups rely on.

    Existing entry data stays where it is; new data is appended. The TOC and name table are
    rewritten in place and must fit the capacities stored in the header.
    """
    if not new_entries:
        return bytes(src_bytes)
    import bisect
    import davename
    from dave import read_dave_bytes
    d, magic, ents, ts, ns = read_dave_bytes(src_bytes)
    if magic != b'Dave':
        raise ValueError('only packed-name Dave archives are supported')
    names = davename.names_of(d)
    rows = [(n, e['off'], e['usize'], e['csize']) for n, e in zip(names, ents)]
    out = bytearray(d)
    for name in sorted(new_entries):
        if name in names:
            raise ValueError('entry %s already exists' % name)
        data = new_entries[name]
        packed = deflate_raw(data) if compress else data
        if len(packed) >= len(data): packed = data
        out += b'\0' * ((-len(out)) % ALIGN)
        pos = bisect.bisect_left(names, name)
        names.insert(pos, name)
        rows.insert(pos, (name, len(out), len(data), len(packed)))
        out += packed
    out += b'\0' * ((-len(out)) % ALIGN)
    blob, offs = davename.encode(names)
    new_ts = max(ts, -(-16 * len(rows) // ALIGN) * ALIGN)
    new_ns = max(ns, -(-len(blob) // ALIGN) * ALIGN)
    delta = (new_ts - ts) + (new_ns - ns)
    if delta:
        data_start = 0x800 + ts + ns
        if min(r[1] for r in rows) < data_start:
            raise ValueError('entry data overlaps the header region')
        out = out[:data_start] + b'\0' * delta + out[data_start:]
        rows = [(n, off + delta, us, cs) for n, off, us, cs in rows]
        ts, ns = new_ts, new_ns
        struct.pack_into('<II', out, 8, ts, ns)
    struct.pack_into('<I', out, 4, len(rows))
    out[0x800:0x800 + ts] = b'\0' * ts
    for i, (_, off, us, cs) in enumerate(rows):
        struct.pack_into('<IIII', out, 0x800 + 16 * i, offs[i], off, us, cs)
    out[0x800 + ts:0x800 + ts + ns] = blob + b'\0' * (ns - len(blob))
    return bytes(out)
