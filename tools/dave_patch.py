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


def _anchor(name, orig_names):
    """Existing entry a new entry's data goes after: the last page of the same font, else its fonttex."""
    import re
    m = re.fullmatch(r'(.+)_(\d+)\.tex', name)
    if not m:
        raise ValueError('no layout anchor for new entry %s' % name)
    pages = sorted(n for n in orig_names if re.fullmatch(re.escape(m.group(1)) + r'_\d+\.tex', n))
    if pages: return pages[-1]
    if m.group(1) + '.fonttex' in orig_names: return m.group(1) + '.fonttex'
    raise ValueError('no layout anchor for new entry %s' % name)


def repack(orig_bytes, patched_bytes):
    """Re-lay the entry data of patched_bytes in the data order of orig_bytes.

    The game streams a level archive in its data order; data appended at the end (patch/insert)
    makes it seek back and forth. Rule (reproduces every original archive byte for byte): each entry
    follows the previous one, 2048-aligned if its original offset was, else 32-aligned; an entry that
    started inside or at the previous one (zero-size aliases) keeps that relative offset. New entries
    go right after their anchor (_anchor). Header, TOC order and name table come from patched_bytes.
    """
    from dave import read_dave_bytes
    import davename
    _, _, oents, _, _ = read_dave_bytes(orig_bytes)
    onames = davename.names_of(orig_bytes)
    pd, _, pents, ts, ns = read_dave_bytes(patched_bytes)
    pnames = davename.names_of(patched_bytes)
    pby = {pnames[e['idx']]: e for e in pents}
    oby = {onames[e['idx']]: e for e in oents}
    packed = lambda d, e: bytes(d[e['off']:e['off'] + e['csize']])
    missing = set(oby) - set(pby)
    if missing: raise ValueError('entries removed: %s' % sorted(missing)[:5])
    new_after = {}
    for n in sorted(set(pby) - set(oby)):
        new_after.setdefault(_anchor(n, oby), []).append(n)
    al = lambda x, a: (x + a - 1) // a * a
    data_start = 0x800 + ts + ns
    out = bytearray(patched_bytes[:data_start])
    pos, oend, prev, prevnew, offs = data_start, 0, None, 0, {}

    def put(name, at):
        nonlocal pos
        blob = packed(pd, pby[name])
        if len(out) < at + len(blob): out.extend(b'\0' * (at + len(blob) - len(out)))
        out[at:at + len(blob)] = blob
        offs[name] = at; pos = max(pos, at + len(blob))

    for e in sorted(oents, key=lambda e: (e['off'], e['idx'])):
        name = onames[e['idx']]
        if prev is not None and (e['off'] < oend or e['off'] == prev['off']):
            if packed(pd, pby[name]) != packed(orig_bytes, e):
                raise ValueError('changed entry %s shares data with the previous entry' % name)
            at = prevnew + (e['off'] - prev['off'])
        else:
            at = al(pos, 0x800 if e['off'] % 0x800 == 0 else 32)
        put(name, at)
        oend = max(oend, e['off'] + e['csize']); prev, prevnew = e, at
        for n in new_after.get(name, []):
            put(n, al(pos, 0x800 if e['off'] % 0x800 == 0 else 32))
    out.extend(b'\0' * (al(pos, 0x800) - len(out)))
    del out[al(pos, 0x800):]
    for e in pents:
        struct.pack_into('<I', out, 0x800 + 16 * e['idx'] + 4, offs[pnames[e['idx']]])
    return bytes(out)
