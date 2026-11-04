"""Tests for tools/textcodec.py: reversible tokens for icon glyphs and brace escaping."""
import os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textcodec as tc


def test_icons_become_tokens_and_back():
    raw = 'Press ½ to retry\nPress º to advance ‡¾ †•‣¼'
    s = tc.to_tokens(raw)
    assert s == 'Press {BTN_BD} to retry\nPress {BTN_BA} to advance {ICON_2021}{BTN_BE} {ICON_2020}{ICON_2022}{ICON_2023}{BTN_BC}'
    assert tc.from_tokens(s) == raw


def test_literal_braces_escaped():
    raw = '!@$%^&*(){}[]\\|'
    assert tc.to_tokens(raw) == '!@$%^&*(){{}}[]\\|'
    assert tc.from_tokens(tc.to_tokens(raw)) == raw


def test_unknown_or_broken_token_rejected():
    for bad in ['{BTN_XX}', 'a { b', 'a } b', '{BTN_BD']:
        with pytest.raises(ValueError):
            tc.from_tokens(bad)


def test_tokens_of_lists_in_order():
    assert tc.tokens_of('{BTN_BD} a {{x}} {ICON_2020}') == ['BTN_BD', 'ICON_2020']
