"""GS local-memory swizzle helpers (PSMCT32 <-> PSMT4) for PS2 textures."""
BT32 = [[0,1,4,5,16,17,20,21],[2,3,6,7,18,19,22,23],[8,9,12,13,24,25,28,29],[10,11,14,15,26,27,30,31]]
CT32 = [[0,1,4,5,8,9,12,13],[2,3,6,7,10,11,14,15],[16,17,20,21,24,25,28,29],[18,19,22,23,26,27,30,31],
        [32,33,36,37,40,41,44,45],[34,35,38,39,42,43,46,47],[48,49,52,53,56,57,60,61],[50,51,54,55,58,59,62,63]]
BT4 = [[0,2,8,10],[1,3,9,11],[4,6,12,14],[5,7,13,15],[16,18,24,26],[17,19,25,27],[20,22,28,30],[21,23,29,31]]
_c4 = [
 [0,8,32,40,64,72,96,104,2,10,34,42,66,74,98,106,4,12,36,44,68,76,100,108,6,14,38,46,70,78,102,110],
 [16,24,48,56,80,88,112,120,18,26,50,58,82,90,114,122,20,28,52,60,84,92,116,124,22,30,54,62,86,94,118,126],
 [65,73,97,105,1,9,33,41,67,75,99,107,3,11,35,43,69,77,101,109,5,13,37,45,71,79,103,111,7,15,39,47],
 [81,89,113,121,17,25,49,57,83,91,115,123,19,27,51,59,85,93,117,125,21,29,53,61,87,95,119,127,23,31,55,63],
 [192,200,224,232,128,136,160,168,194,202,226,234,130,138,162,170,196,204,228,236,132,140,164,172,198,206,230,238,134,142,166,174],
 [208,216,240,248,144,152,176,184,210,218,242,250,146,154,178,186,212,220,244,252,148,156,180,188,214,222,246,254,150,158,182,190],
 [129,137,161,169,193,201,225,233,131,139,163,171,195,203,227,235,133,141,165,173,197,205,229,237,135,143,167,175,199,207,231,239],
 [145,153,177,185,209,217,241,249,147,155,179,187,211,219,243,251,149,157,181,189,213,221,245,253,151,159,183,191,215,223,247,255]]
CT4 = _c4 + [[v + 256 for v in r] for r in _c4]

def addr32(x, y, bw):  # bw in pages (64px)
    page = (y // 32) * bw + (x // 64)
    blk = BT32[(y % 32) // 8][(x % 64) // 8]
    word = CT32[y % 8][x % 8]
    return (page * 2048 + blk * 64 + word) * 4  # byte address

def addr4(x, y, bw):  # bw in pages (128px); returns nibble address
    page = (y // 128) * bw + (x // 128)
    blk = BT4[(y % 128) // 16][(x % 128) // 32]
    nib = CT4[y % 16][x % 32]
    return page * 8192 * 2 + blk * 512 + nib

def ct32_to_t4(data, w, h):
    """data = bytes uploaded linearly as PSMCT32 image of (w/2 x h/4)? -> generic: place into memory, read as T4."""
    raise NotImplementedError

def unswizzle4(data, w, h):
    """Interpret `data` as a PSMCT32 rect (w//2 wide? see below) written at 0 and read back as PSMT4 w x h."""
    cw, ch = w // 2, h // 4  # 4bpp WxH occupies same bytes as CT32 (W/2 x H/4)?? caller verifies visually
    mem = bytearray(max(len(data), w * h // 2) * 2)
    bw32 = max(1, cw // 64)
    i = 0
    for y in range(ch):
        for x in range(cw):
            a = addr32(x, y, bw32)
            mem[a:a + 4] = data[i:i + 4]; i += 4
    out = bytearray(w * h)
    bw4 = max(1, w // 128)
    for y in range(h):
        for x in range(w):
            n = addr4(x, y, bw4)
            b = mem[n >> 1]
            out[y * w + x] = (b >> 4) if n & 1 else (b & 15)
    return bytes(out)

def _maps(W, H):
    cw, ch = W // 4, H // 4  # PSMT4 WxH stored as PSMCT32 (W/4 x H/4)? verified: 512x256 <-> 128x128? see below
    raise NotImplementedError

def _ct_dims(W, H):
    # 512x256 4bpp = 64KB = 128x128 CT32 (verified). General: CT32 width = W/4? 512/4=128, H*W/2/4/128 rows.
    # Empirical (visually verified): 512x256->128x128, 256x256->128x64, 256x128->64x64, 128x64->32x32
    import math
    n = W * H // 8
    cw = 1 << math.ceil(math.log2(math.sqrt(n)))
    return cw, n // cw

def t4_from_ct32(data, W, H):
    cw, ch = _ct_dims(W, H)
    mem = {}
    bw32 = max(1, cw // 64)
    i = 0
    for y in range(ch):
        for x in range(cw):
            a = addr32(x, y, bw32)
            for k in range(4): mem[a + k] = data[i + k]
            i += 4
    out = bytearray(W * H)
    bw4 = max(1, W // 128)
    for y in range(H):
        for x in range(W):
            n = addr4(x, y, bw4)
            b = mem.get(n >> 1, 0)
            out[y * W + x] = (b >> 4) if n & 1 else (b & 15)
    return bytes(out)

def ct32_from_t4(pixels, W, H):
    cw, ch = _ct_dims(W, H)
    mem = {}
    bw4 = max(1, W // 128)
    for y in range(H):
        for x in range(W):
            n = addr4(x, y, bw4)
            b = mem.get(n >> 1, 0)
            v = pixels[y * W + x] & 15
            b = (b & 0x0F) | (v << 4) if n & 1 else (b & 0xF0) | v
            mem[n >> 1] = b
    out = bytearray(cw * ch * 4)
    bw32 = max(1, cw // 64)
    i = 0
    for y in range(ch):
        for x in range(cw):
            a = addr32(x, y, bw32)
            for k in range(4): out[i + k] = mem.get(a + k, 0)
            i += 4
    return bytes(out)
