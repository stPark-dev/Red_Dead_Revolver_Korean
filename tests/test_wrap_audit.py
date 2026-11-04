"""Tests for tools/wrap_audit.py: greedy word wrap of the HUD text boxes and lone-word (orphan) detection."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import wrap_audit as wa

# every glyph 10 wide, tracking 1, space 5  ->  'aa' = 22, 'aa aa' = 49
M = dict(widths={ord(c): 10 for c in 'abcdefg가나다라마'}, space=5, tracking=1)


def test_width_matches_build_metrics():
    assert wa.width('aa', **M) == 22 and wa.width('aa aa', **M) == 49


def test_wrap_is_greedy_on_spaces_and_honours_newlines():
    assert wa.wrap('aa aa aa', 49, **M) == ['aa aa', 'aa']
    assert wa.wrap('aa aa aa', 76, **M) == ['aa aa aa']
    assert wa.wrap('aa\naa aa', 76, **M) == ['aa', 'aa aa']


def test_orphan_is_short_last_line_only():
    assert wa.orphan('aaaa aaaa a', 100, **M)          # 'aaaa aaaa' | 'a' (11 < 20% of 100)
    assert not wa.orphan('aaaa aaaa', 100, **M)        # one line
    assert not wa.orphan('aaaa aaaa aaaa', 100, **M)   # last line 44 wide


def test_audit_flags_only_korean_introduced_orphans():
    src = {'t/x': dict(id='t/x', font='berrylium', sx=0.8, src='bbbb bbbb'),
           't/y': dict(id='t/y', font='berrylium', sx=0.8, src='cccc cccc c'),
           't/z': dict(id='t/z', font='steelfish', sx=0.8, src='dddd')}
    recs = [dict(id='t/x', ko='가나다라 가나다라 가'), dict(id='t/y', ko='가나다라 가나다라 가'),
            dict(id='t/z', ko='가나다라 가나다라 가')]
    hits = wa.audit(src, recs, {'berrylium': M}, limits=(100,))
    assert [h['id'] for h in hits] == ['t/x']       # y: English already orphaned; z: other font
    assert hits[0]['lines'] == ['가나다라 가나다라', '가'] and hits[0]['limit'] == 100


def test_glyphless_source_characters_count_as_zero_width():
    # the original game drops characters its fonts lack (e.g. U+2026); the audit must not crash on them
    assert wa.width('aa…', **M) == 22


def test_explicit_newline_is_not_an_orphan():
    assert not wa.orphan('aaaa aaaa\na', 100, **M)      # author-placed break, not a wrap
    assert wa.orphan('a\naaaa aaaa a', 100, **M)        # wrap inside the last paragraph still counts
