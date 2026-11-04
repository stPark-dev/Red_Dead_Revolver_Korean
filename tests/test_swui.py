"""Tests for tools/swui.py: layout scripts -> (font, reference) uses."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import swui

SAMPLE = """; comment <TEXT:0,0,0:Ignored>
<LOOKUP:BookContents>
<LOOKUPDATA:lvl_perfnew_1,\tChapter 1,\tBOOK_PERFNEW,\timg0_perfnew,\tBOOK_PERFNEW_DESC>
<FONT:steelfish>
<TEXT:131,12,0:ALIGN:center:chapter_heading0><BASECOLOR:0,0,0,0.800>
<FONT:RegulatorCondensed:SCALE:0.900,1.179>
<TEXT:126,45,0:SCALE:1.304,1:ALIGN:center:chapter_title0>
<FONT:berrylium>
<TEXTBOX:24,85,0:244:SCALE:0.728,0.500:chapter_description0><BASECOLOR:0,0,0,1>
<READOUT:20,240,0:BASELINE:center:pagenum_left>
<TEXT:220,388,0:NAME:PROMPT1:Enter>
<TEXT:315,24,0:book_instr_left> ; trailing comment <TEXT:1,1,1:Nope>
"""


def test_uses_track_font_state_and_skip_comments():
    uses = swui.text_uses(SAMPLE)
    assert ('steelfish', 'chapter_heading0') in uses
    assert ('regulatorcondensed', 'chapter_title0') in uses
    assert ('berrylium', 'chapter_description0') in uses
    assert ('berrylium', 'pagenum_left') in uses
    assert ('berrylium', 'Enter') in uses and ('berrylium', 'book_instr_left') in uses
    assert not any(r in ('Ignored', 'Nope') for _, r in uses)


def test_lookup_rows():
    rows = swui.lookup_rows(SAMPLE)
    assert rows == {'BookContents': [['lvl_perfnew_1', 'Chapter 1', 'BOOK_PERFNEW', 'img0_perfnew', 'BOOK_PERFNEW_DESC']]}


def test_fonts_for_refs_with_lookup_map():
    lookup_map = {'BookContents': [None, 'chapter_heading0', 'chapter_title0', None, 'chapter_description0']}
    fonts = swui.ref_fonts(SAMPLE, lookup_map)
    assert fonts['Chapter 1'] == {'steelfish'}
    assert fonts['BOOK_PERFNEW'] == {'regulatorcondensed'}
    assert fonts['BOOK_PERFNEW_DESC'] == {'berrylium'}
    assert fonts['Enter'] == {'berrylium'}


def test_unmapped_lookup_cells_get_all_fonts_of_the_file():
    fonts = swui.ref_fonts(SAMPLE, {})
    assert fonts['Chapter 1'] == {'steelfish', 'regulatorcondensed', 'berrylium'}


def test_button_combo_and_combodata_labels():
    text = """<FONT:berrylium>
<BUTTON:250,193,0:Restart Level:RESET:0,0:640,448:0:-1:0>
<COMBO:80,300,0:Widescreen:347,300:200,24:10>
<COMBODATA:Off:0>
"""
    uses = swui.text_uses(text)
    assert ('berrylium', 'Restart Level') in uses
    assert ('berrylium', 'Widescreen') in uses
    assert ('berrylium', 'Off') in uses
