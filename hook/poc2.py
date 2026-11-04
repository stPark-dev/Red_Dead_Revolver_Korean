"""PoC2 hook + patcher assembly (keystone). Addresses verified against RAM dumps of SLUS_205.00 (CRC E169BAF8)."""
import struct
import keystone as K

HOOK_BASE = 0x1F50000
LOOKUP = 0x3FC3A8
SITES = {  # call site -> (expected word, string-pointer register)
    0x3FC4C8: (0x0C0FF0EA, 's0'),   # measure/wrap loop
    0x3FC860: (0x0C0FF0EA, 's1'),   # draw loop
}
HEAP_END_SITE = (0x21A018, 0x3C0401F6, 0x3C0401F5)  # lui a0,0x1f6 -> 0x1f5 (reserve 64KB)
STUB_JUMP = (0x800020, 0x08040002)  # j 0x100008 in unpacker stub

ks = K.Ks(K.KS_ARCH_MIPS, K.KS_MODE_MIPS32 + K.KS_MODE_LITTLE_ENDIAN)

def asm(src, addr):
    enc, _ = ks.asm('.set noreorder\n' + src, addr)
    return bytes(enc)

def wrapper(reg, n):
    return f"""
w{n}:
    andi  $t0, $a1, 0xff
    sltiu $t1, $t0, 0xb0
    bnez  $t1, o{n}
    sltiu $t1, $t0, 0xc9
    beqz  $t1, o{n}
    lbu   $t2, 0(${reg})
    sltiu $t1, $t2, 0xa1
    bnez  $t1, o{n}
    sltiu $t1, $t2, 0xff
    beqz  $t1, o{n}
    nop
    addiu ${reg}, ${reg}, 1
    j     {LOOKUP:#x}
    addiu $a1, $zero, 0x40
o{n}:
    j     {LOOKUP:#x}
    nop
"""

def build_hook():
    src = ''; entries = {}
    for n, (site, (_, reg)) in enumerate(sorted(SITES.items())):
        src += wrapper(reg, n)
    blob = asm(src, HOOK_BASE)
    # entry addresses: each wrapper is 16 instructions
    for n, site in enumerate(sorted(SITES)):
        entries[site] = HOOK_BASE + n * 16 * 4
    return blob, entries

def jal(target): return 0x0C000000 | ((target >> 2) & 0x03FFFFFF)

def build_patcher(patcher_addr, blob, patches):
    """patches: list of (addr, value). Layout: code | table | blob."""
    nwords = (len(blob) + 3) // 4
    code_len = 4 * 40
    table_addr = patcher_addr + code_len
    blob_addr = table_addr + 8 * len(patches)
    hi = lambda v: (v >> 16) & 0xFFFF; lo = lambda v: v & 0xFFFF
    src = f"""
    lui   $t0, {hi(blob_addr):#x}
    ori   $t0, $t0, {lo(blob_addr):#x}
    lui   $t1, {hi(HOOK_BASE):#x}
    ori   $t1, $t1, {lo(HOOK_BASE):#x}
    ori   $t2, $zero, {nwords:#x}
cp:
    lw    $t3, 0($t0)
    addiu $t0, $t0, 4
    sw    $t3, 0($t1)
    addiu $t2, $t2, -1
    bnez  $t2, cp
    addiu $t1, $t1, 4
    lui   $t0, {hi(table_addr):#x}
    ori   $t0, $t0, {lo(table_addr):#x}
    ori   $t2, $zero, {len(patches):#x}
pl:
    lw    $t1, 0($t0)
    lw    $t3, 4($t0)
    sw    $t3, 0($t1)
    addiu $t2, $t2, -1
    bnez  $t2, pl
    addiu $t0, $t0, 8
    addiu $v1, $zero, 0x64
    move  $a0, $zero
    syscall
    addiu $v1, $zero, 0x64
    addiu $a0, $zero, 2
    syscall
    j     0x100008
    nop
"""
    code = asm(src, patcher_addr)
    assert len(code) <= code_len, len(code)
    code += b'\0' * (code_len - len(code))
    table = b''.join(struct.pack('<II', a, v) for a, v in patches)
    return code + table + blob + b'\0' * (4 * nwords - len(blob))

def patch_elf(elf, verify_ram=None):
    """Return patched ELF bytes. verify_ram: decompressed RAM image to check expected words."""
    e = bytearray(elf)
    phoff = struct.unpack_from('<I', e, 0x1C)[0]
    p_off, p_vaddr, _, p_filesz, p_memsz = struct.unpack_from('<IIIII', e, phoff + 4)
    assert p_vaddr == 0x800000 and p_off == 0x1000
    sj_addr, sj_word = STUB_JUMP
    assert struct.unpack_from('<I', e, p_off + sj_addr - p_vaddr)[0] == sj_word, 'stub jump mismatch'
    blob, entries = build_hook()
    patches = []
    for site, (expect, _) in SITES.items():
        if verify_ram is not None:
            assert struct.unpack_from('<I', verify_ram, site)[0] == expect, hex(site)
        patches.append((site, jal(entries[site])))
    a, expect, new = HEAP_END_SITE
    if verify_ram is not None:
        assert struct.unpack_from('<I', verify_ram, a)[0] == expect
    patches.append((a, new))
    patcher_addr = (p_vaddr + p_filesz + 15) & ~15
    payload = build_patcher(patcher_addr, blob, patches)
    end = p_off + (patcher_addr - p_vaddr)
    e = e[:p_off + p_filesz] + b'\0' * (end - (p_off + p_filesz)) + payload
    newsz = patcher_addr + len(payload) - p_vaddr
    struct.pack_into('<II', e, phoff + 16, newsz, newsz)
    struct.pack_into('<I', e, 0x20, 0)            # e_shoff
    struct.pack_into('<HHH', e, 0x2E, 0, 0, 0)    # shentsize, shnum, shstrndx
    j = 0x08000000 | ((patcher_addr >> 2) & 0x03FFFFFF)
    struct.pack_into('<I', e, p_off + sj_addr - p_vaddr, j)
    return bytes(e), patcher_addr, blob, patches
