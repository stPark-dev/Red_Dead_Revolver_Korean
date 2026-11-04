"""Tests for tools/ipu.py: PS2 IPU still images (MPEG-2 intra macroblocks, no slice headers)."""
import os, sys, shutil, subprocess, glob
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import ipu

SWAT = os.path.join(ROOT, 'work', 'iso', 'SWAT.DAT')


def gradient(w, h):
    y, x = np.mgrid[0:h, 0:w]
    rgb = np.stack([(x * 255 // max(w - 1, 1)), (y * 255 // max(h - 1, 1)), ((x + y) * 3) % 256], -1)
    return rgb.astype(np.uint8)


def test_encode_then_parse_build_is_byte_exact():
    b = ipu.encode(gradient(64, 48), q=2)
    assert b[:4] == b'ipum'
    doc = ipu.parse(b)
    assert (doc['w'], doc['h'], doc['flags']) == (64, 48, 0)
    assert len(doc['mbs']) == 4 * 3
    assert ipu.build(doc) == b


def test_header_and_trailer_match_game_files():
    b = ipu.encode(gradient(32, 32), q=2)
    size, w, h, n = np.frombuffer(b[4:16], dtype='<u4')[0], b[8] | b[9] << 8, b[10] | b[11] << 8, b[12]
    assert size == len(b) - 8 and (w, h, n) == (32, 32, 1)
    assert b[-8:] == bytes.fromhex('000001b0000001b1')


def test_decode_reproduces_image():
    img = gradient(64, 48)
    out = ipu.decode(ipu.parse(ipu.encode(img, q=1)))
    assert out.shape == img.shape
    assert np.abs(out.astype(int) - img.astype(int)).mean() < 3


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg missing')
def test_ffmpeg_decodes_our_bitstream_like_our_decoder(tmp_path):
    img = gradient(64, 48)
    b = ipu.encode(img, q=3)
    p = tmp_path / 'x.ipu'; p.write_bytes(b)
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'ipu', '-i', str(p), '-frames:v', '1',
                          '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'], capture_output=True, check=True).stdout
    assert len(raw) == 64 * 48 * 3 // 2
    ours = ipu.decode_yuv(ipu.parse(b))
    theirs = np.frombuffer(raw[:64 * 48], np.uint8).reshape(48, 64)
    assert np.abs(ours[0].astype(int) - theirs.astype(int)).max() <= 2


def test_replace_region_keeps_untouched_macroblocks_bit_identical():
    doc = ipu.parse(ipu.encode(gradient(64, 48), q=2))
    new = np.full((48, 64, 3), 200, np.uint8)
    out = ipu.replace_region(doc, new, (16, 16, 32, 32), q=1)  # x0, y0, x1, y1 -> exactly macroblock (1,1)
    changed = [i for i, (a, b) in enumerate(zip(ipu.effective_mbs(doc), ipu.effective_mbs(out))) if a != b]
    assert changed == [1 * 4 + 1]
    assert ipu.parse(ipu.build(out)) == out
    px = ipu.decode(out)
    assert np.abs(px[16:32, 16:32].astype(int) - 200).max() <= 3
    assert doc['mbs'][0] == ipu.parse(ipu.build(doc))['mbs'][0]  # input untouched


def test_replace_region_snaps_to_macroblock_grid():
    doc = ipu.parse(ipu.encode(gradient(64, 48), q=2))
    out = ipu.replace_region(doc, gradient(64, 48)[::-1].copy(), (17, 3, 18, 4), q=2)
    changed = [i for i, (a, b) in enumerate(zip(ipu.effective_mbs(doc), ipu.effective_mbs(out))) if a != b]
    assert changed == [1]


def test_parse_rejects_bad_magic():
    with pytest.raises(ValueError):
        ipu.parse(b'xxxx' + bytes(12))


def game_ipus():
    if not os.path.exists(SWAT): return []
    import dave, davename
    d, _, ents, _, _ = dave.read_dave(SWAT)
    return [(n, dave.entry_data(d, e)) for n, e in zip(davename.names_of(d), ents)
            if n.startswith('mpload_gen_0') and n.endswith('.ipu')][:2]


@pytest.mark.skipif(not os.path.exists(SWAT), reason='extracted SWAT.DAT missing')
def test_game_files_round_trip_byte_exact():
    files = game_ipus()
    assert files
    for name, b in files:
        assert ipu.build(ipu.parse(b)) == b, name
