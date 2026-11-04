"""Tests for tools/pupshow.py: cutscene subtitle files (UTF-16LE, tab-separated time/line1/line2/duration)."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pupshow


def enc(text, tail=b''):
    return b'\xff\xfe' + text.encode('utf-16-le') + tail


SAMPLE = '00:14.0\tDarlin!\tPa!\t5\r\n00:25.0\t"Hey Pa, where did you get that?"\t\t5\r\n00:32.0\tWhere\'s it? \t\t5\r\n'


def test_round_trip_exact():
    b = enc(SAMPLE)
    assert pupshow.build(pupshow.parse(b)) == b


def test_round_trip_keeps_odd_trailing_byte():
    b = enc(SAMPLE, tail=b'\x00')
    assert pupshow.build(pupshow.parse(b)) == b


def test_display_text_strips_quotes_and_padding():
    cues = pupshow.cues(pupshow.parse(enc(SAMPLE)))
    assert [pupshow.display(c) for c in cues] == ['Darlin!\nPa!', 'Hey Pa, where did you get that?', "Where's it?"]


def test_set_text_writes_unquoted_lines_and_keeps_timing():
    doc = pupshow.parse(enc(SAMPLE))
    new = pupshow.with_text(doc, {0: '여보!\n아버지!', 1: '아버지, 그거 어디서 났어요?'})
    out = pupshow.build(new).decode('utf-16')
    assert out.split('\r\n')[:3] == ['00:14.0\t여보!\t아버지!\t5', '00:25.0\t아버지, 그거 어디서 났어요?\t\t5',
                                     "00:32.0\tWhere's it? \t\t5"]
    assert pupshow.cues(doc)[0]['l1'] == 'Darlin!'  # input untouched


JUNK = '00:03.0\tHi.\t\t5\r\n\r\n\t \t\t\r\n \t\t\t\r\n00:09.0\tBye.\t\t5\r\n'


def test_lines_without_time_are_kept_and_not_cues():
    doc = pupshow.parse(enc(JUNK))
    assert [pupshow.display(c) for c in pupshow.cues(doc)] == ['Hi.', 'Bye.']
    assert pupshow.build(doc) == enc(JUNK)
    out = pupshow.build(pupshow.with_text(doc, {1: '잘 가.'})).decode('utf-16')
    assert out.endswith('\r\n00:09.0\t잘 가.\t\t5\r\n') and '\t \t\t\r\n' in out


@pytest.mark.parametrize('bad', ['a\nb\nc', 'a\tb', '"quoted"'])
def test_set_text_rejects_unrepresentable(bad):
    with pytest.raises(ValueError):
        pupshow.with_text(pupshow.parse(enc(SAMPLE)), {0: bad})


def test_line_width_uses_glyph_widths_and_space():
    widths = {ord('A'): 20, ord('가'): 22}
    assert pupshow.line_width('AA 가', widths, space=8) == 70
    assert pupshow.too_wide({'x': '가' * 3 + '\n' + 'A'}, widths, limit=60, space=8) == ['x: line 1 width 66 > 60']
    assert pupshow.too_wide({'x': '가가\nA'}, widths, limit=60, space=8) == []


def test_records_from_files():
    recs = pupshow.records({'lvl_a_pupshow_01_en.txt': enc(SAMPLE)}, copies={'lvl_a_pupshow_01_en.txt': ['A.DAT']})
    assert recs[0] == dict(id='pupshow/lvl_a_pupshow_01_en.txt/0', table='lvl_a_pupshow_01_en.txt', key='0',
                           font='berrylium', src='Darlin!\nPa!', time='00:14.0', copies=['A.DAT'], reach='game')
    assert [r['key'] for r in recs] == ['0', '1', '2']
