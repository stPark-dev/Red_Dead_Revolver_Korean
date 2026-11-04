"""Minimal ISO9660 file replace: in place if it fits its sectors, else append and repoint."""
import struct
SEC = 2048

def _dir_records(img, lba, size):
    pos = lba * SEC; end = pos + size
    while pos < end:
        ln = img[pos]
        if ln == 0:
            pos = (pos // SEC + 1) * SEC; continue
        yield pos, img[pos:pos + ln]; pos += ln

def find(img, path):
    root = img[16 * SEC + 156:16 * SEC + 156 + 34]
    lba, size = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
    parts = path.upper().strip('/').split('/')
    for i, p in enumerate(parts):
        for pos, rec in _dir_records(img, lba, size):
            nl = rec[32]; name = rec[33:33 + nl].decode('ascii', 'replace').split(';')[0]
            if name == p:
                lba = struct.unpack_from('<I', rec, 2)[0]; size = struct.unpack_from('<I', rec, 10)[0]
                if i == len(parts) - 1:
                    return pos, lba, size
                break
        else:
            raise FileNotFoundError(path)

def replace(img, path, data):
    """img: bytearray (modified in place, may grow). Returns (lba, mode)."""
    pos, lba, size = find(img, path)
    cap = (size + SEC - 1) // SEC * SEC
    if len(data) <= cap:
        img[lba * SEC:lba * SEC + cap] = data + b'\0' * (cap - len(data)); mode = 'inplace'
    else:
        if len(img) % SEC: raise ValueError('image not sector aligned')
        lba = len(img) // SEC
        img += data + b'\0' * ((-len(data)) % SEC); mode = 'append'
        total = len(img) // SEC
        struct.pack_into('<I', img, 16 * SEC + 80, total); struct.pack_into('>I', img, 16 * SEC + 84, total)
    struct.pack_into('<I', img, pos + 2, lba); struct.pack_into('>I', img, pos + 6, lba)
    struct.pack_into('<I', img, pos + 10, len(data)); struct.pack_into('>I', img, pos + 14, len(data))
    return lba, mode

def finalize(img, pad_sectors=2048):
    """Pad image tail (game reads ahead past file ends) and update volume size."""
    img += b'\0' * (pad_sectors * SEC)
    total = len(img) // SEC
    struct.pack_into('<I', img, 16 * SEC + 80, total); struct.pack_into('>I', img, 16 * SEC + 84, total)

def list_files(img):
    """[(path, lba, size)] for every file, depth-first, '/'-separated, without ';1'."""
    root = img[16 * SEC + 156:16 * SEC + 156 + 34]
    out = []
    def walk(lba, size, prefix):
        for pos, rec in _dir_records(img, lba, size):
            nl = rec[32]; raw = rec[33:33 + nl]
            if raw in (b'\0', b'\1'): continue
            name = raw.decode('ascii', 'replace').split(';')[0]
            clba, csize = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
            if rec[25] & 2: walk(clba, csize, prefix + name + '/')
            else: out.append((prefix + name, clba, csize))
    walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
    return out
