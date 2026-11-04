"""Print free memory of the main game heap via PINE.

Heap object pointer at 0x79DD80: +4 base, +8 size, +0xC used (bump top); free lists at +0x20 (32 bins),
block {+4 size, +0x14 next}. Allocation fails ("Heap overrun") when used would exceed size.
"""
import sys
sys.path.insert(0, 'tools')
import pine

p = pine.Pine()
h = p.read32(0x79DD80)
base, size, used = p.read32(h + 4), p.read32(h + 8), p.read32(h + 0xC)
binfree = nblk = 0
for b in range(32):
    q, k = p.read32(h + 0x20 + 4 * b), 0
    while q and k < 5000:
        binfree += p.read32(q + 4); nblk += 1; k += 1
        q = p.read32(q + 0x14)
print('heap %#x base %#x size %d used %d top_free %d binfree %d (%d blocks) total_free %d' % (
    h, base, size, used, size - used, binfree, nblk, size - used + binfree))
