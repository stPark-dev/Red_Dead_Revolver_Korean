"""Locate and edit bitmap fonts inside Angel UI bundle images (RDR PS2).

Bundle = 16-byte header {u32 base, u32 1, u32 0, u32 imageSize} + memory image at `base`.
Font object (verified on FRONT/0094): +4 vtable 0x159E58, +8 glyphCount, +0x10 codeList*,
+0x14 advance*, +0x18 ascii table[128], +0x98 variantCount, +0x9C variant*[n].
Variant: +0 tex*, +4 f32 1/W, +8 f32 1/H, +0xC glyph*(12B each: u8 x/2, u8 y, u8 w, u8 h, s16 x0,y0,x1,y1).
Texture: *(tex+0x94) = image header; *(imghdr+8) = pixels (PSMT4 stored as PSMCT32 W/4 x H/4... see gsmem).
"""
import struct
import gsmem

FONT_VTABLE = 0x159E58

class Bundle:
    def __init__(self, data):
        self.d = bytearray(data)
        self.base = struct.unpack_from('<I', data, 0)[0] - 0x10
    def off(self, addr): return addr - self.base
    def u32(self, addr): return struct.unpack_from('<I', self.d, self.off(addr))[0]
    def f32(self, addr): return struct.unpack_from('<f', self.d, self.off(addr))[0]
    def contains(self, addr): return 0x10 <= addr - self.base < len(self.d)

    def fonts(self):
        out = []
        for o in range(0x10, len(self.d) - 0xA0, 4):
            if struct.unpack_from('<I', self.d, o)[0] != FONT_VTABLE: continue
            obj = self.base + o - 4
            n = self.u32(obj + 8)
            if not 0 < n <= 4096: continue
            cl = self.u32(obj + 0x10)
            if not self.contains(cl): continue
            nv = self.u32(obj + 0x98)
            if not 0 < nv <= 8: continue
            codes = struct.unpack_from('<%dH' % n, self.d, self.off(cl))
            variants = []
            for i in range(nv):
                v = self.u32(obj + 0x9C + 4 * i)
                tex = self.u32(v); su = self.f32(v + 4); sv = self.f32(v + 8); gl = self.u32(v + 0xC)
                img = self.u32(tex + 0x94); pix = self.u32(img + 8)
                W, H = round(1 / su), round(1 / sv)
                variants.append(dict(addr=v, tex=tex, W=W, H=H, glyphs=gl, pixels=pix))
            out.append(dict(obj=obj, n=n, codes=codes, adv=self.u32(obj + 0x14), variants=variants))
        return out

    def glyph(self, var, i):
        return list(struct.unpack_from('<BBBBhhhh', self.d, self.off(var['glyphs'] + 12 * i)))
    def set_glyph(self, var, i, g):
        struct.pack_into('<BBBBhhhh', self.d, self.off(var['glyphs'] + 12 * i), *g)

    def read_t4(self, var):
        W, H = var['W'], var['H']
        o = self.off(var['pixels'])
        return bytearray(gsmem.t4_from_ct32(bytes(self.d[o:o + W * H // 2]), W, H))
    def write_t4(self, var, pixels):
        W, H = var['W'], var['H']
        o = self.off(var['pixels'])
        self.d[o:o + W * H // 2] = gsmem.ct32_from_t4(pixels, W, H)
