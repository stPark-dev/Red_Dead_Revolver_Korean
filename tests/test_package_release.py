"""Tests for tools/package_release.py: distribution zip (xdelta + Windows/Linux appliers + notices) from a beta/release build."""
import hashlib, os, shutil, subprocess, sys, zipfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import package_release as pr

need_xdelta = pytest.mark.skipif(shutil.which('xdelta3') is None, reason='xdelta3 missing')


def sha1(b): return hashlib.sha1(b).hexdigest()


def fixture(tmp_path, policy='beta'):
    src = os.urandom(200_000); out = src[:50_000] + b'KOREAN' * 1000 + src[60_000:]
    (tmp_path / 'src.iso').write_bytes(src); (tmp_path / 'out.iso').write_bytes(out)
    (tmp_path / 'dec.exe').write_bytes(b'MZ fake decoder'); (tmp_path / 'lic.txt').write_text('license')
    manifest = dict(policy=policy, source_sha1=sha1(src), out_sha1=sha1(out), source_commit='abc123')
    return src, out, manifest


def make(tmp_path, manifest, **kw):
    return pr.make_package(tmp_path / 'pkg', str(tmp_path / 'src.iso'), str(tmp_path / 'out.iso'), manifest,
                           version='0.9.0-beta.1', decoder=str(tmp_path / 'dec.exe'),
                           licenses={'xdelta3-Apache-2.0.txt': str(tmp_path / 'lic.txt')},
                           urls=dict(REPO_URL='https://example.org/repo', SITE_URL='https://example.org/site'), **kw)


def test_render_fills_placeholders_and_rejects_leftovers():
    assert pr.render('v{{VERSION}} {{X}}', dict(VERSION='1', X='y')) == 'v1 y'
    with pytest.raises(ValueError, match='MISSING'):
        pr.render('{{MISSING}}', {})


@need_xdelta
def test_package_contents_and_linux_apply_round_trip(tmp_path):
    src, out, manifest = fixture(tmp_path)
    pkg = make(tmp_path, manifest)
    names = {p.relative_to(pkg).as_posix() for p in pkg.rglob('*') if p.is_file()}
    assert {'apply.sh', '한글패치_적용.bat', '읽어주세요.txt', 'DISTRIBUTION_NOTICE.txt', 'THIRD_PARTY_NOTICES.txt',
            'VERSION.txt', 'CHECKSUMS.sha256', 'tools/xdelta3decode.exe', 'licenses/xdelta3-Apache-2.0.txt'} <= names
    assert any(n.startswith('patch/') and n.endswith('.xdelta') for n in names)
    bat = (pkg / '한글패치_적용.bat').read_bytes()
    assert b'\r\n' in bat and b'{{' not in bat and not bat.startswith(b'\xef\xbb\xbf')
    assert (pkg / '읽어주세요.txt').read_bytes().startswith(b'\xef\xbb\xbf')
    assert b'\r\n' not in (pkg / 'apply.sh').read_bytes()
    r = subprocess.run(['sh', str(pkg / 'apply.sh'), str(tmp_path / 'src.iso')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    result = [p for p in pkg.glob('*.iso')]
    assert len(result) == 1 and result[0].read_bytes() == out


@need_xdelta
def test_linux_apply_rejects_wrong_source(tmp_path):
    src, out, manifest = fixture(tmp_path)
    pkg = make(tmp_path, manifest)
    (tmp_path / 'other.iso').write_bytes(src[::-1])
    r = subprocess.run(['sh', str(pkg / 'apply.sh'), str(tmp_path / 'other.iso')], capture_output=True, text=True)
    assert r.returncode != 0 and 'SLUS-20500' in r.stderr and not list(pkg.glob('*.iso'))


@need_xdelta
def test_package_refuses_dev_builds_and_mismatched_inputs(tmp_path):
    _, _, manifest = fixture(tmp_path, policy='dev')
    with pytest.raises(SystemExit, match='dev'):
        make(tmp_path, manifest)
    _, _, manifest = fixture(tmp_path)
    with pytest.raises(SystemExit, match='out_sha1'):
        make(tmp_path, dict(manifest, out_sha1='0' * 40))


@need_xdelta
def test_zip_holds_package_under_its_name(tmp_path):
    _, _, manifest = fixture(tmp_path)
    pkg = make(tmp_path, manifest)
    archive = pr.zip_package(pkg, tmp_path / 'p.zip')
    with zipfile.ZipFile(archive) as z:
        assert 'pkg/apply.sh' in z.namelist()
        assert z.getinfo('pkg/apply.sh').external_attr >> 16 & 0o111   # executable bit kept


DECODER = os.environ.get('XDELTA3DECODE_EXE', os.path.join(ROOT, '..', 'jojo', 'work', 'tools',
                                                          'xdelta3-3.2.2-windows-x86_64', 'xdelta3decode.exe'))
need_wine = pytest.mark.skipif(shutil.which('wine') is None or not os.path.exists(DECODER),
                               reason='wine or xdelta3decode.exe missing')


def run_bat(pkg, *args):
    env = dict(os.environ, WINEDEBUG='-all')
    return subprocess.run(['wine', 'cmd', '/c', '한글패치_적용.bat', *args], cwd=pkg, input=b'\n',
                          capture_output=True, env=env, timeout=300)


def winpath(p): return 'Z:' + str(p).replace('/', '\\')


@need_xdelta
@need_wine
def test_windows_bat_under_wine(tmp_path):
    src, out, manifest = fixture(tmp_path)
    pkg = pr.make_package(tmp_path / 'pkg', str(tmp_path / 'src.iso'), str(tmp_path / 'out.iso'), manifest,
                          version='0.9.0-beta.1', decoder=DECODER, licenses={})
    result = pkg / 'RedDeadRevolver_KR_v0.9.0-beta.1.iso'
    run_bat(pkg, winpath(tmp_path / 'src.iso'))                       # ISO dropped on the .bat
    assert result.read_bytes() == out
    before = result.stat().st_mtime_ns
    run_bat(pkg, winpath(tmp_path / 'src.iso'))                       # existing output is never overwritten
    assert result.stat().st_mtime_ns == before
    result.unlink()
    shutil.copy(tmp_path / 'src.iso', pkg / 'Red Dead Revolver (USA).iso')
    run_bat(pkg)                                                      # double-click with the ISO in the folder
    assert result.read_bytes() == out
    result.unlink(); (pkg / 'Red Dead Revolver (USA).iso').unlink()
    (tmp_path / 'wrong.iso').write_bytes(src[::-1])
    run_bat(pkg, winpath(tmp_path / 'wrong.iso'))                     # wrong source: no output left behind
    assert not result.exists()
