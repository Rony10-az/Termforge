import pytest

from termforge import jsonc


def test_line_and_block_comments():
    text = '{"a": 1, // uno\n "b": /* dos */ 2}'
    assert jsonc.loads(text) == {"a": 1, "b": 2}


def test_trailing_commas():
    assert jsonc.loads('{"a": [1, 2,], "b": {"c": 3,},}') == {"a": [1, 2], "b": {"c": 3}}


def test_comment_markers_inside_strings_are_kept():
    text = '{"url": "https://example.com/a//b", "note": "/* no */", "q": "a,]"}'
    assert jsonc.loads(text) == {
        "url": "https://example.com/a//b",
        "note": "/* no */",
        "q": "a,]",
    }


def test_escaped_quote_inside_string():
    assert jsonc.loads(r'{"a": "di \"hola\" // esto queda"}') == {"a": 'di "hola" // esto queda'}


def test_bom_is_ignored():
    assert jsonc.loads('﻿{"a": 1}') == {"a": 1}


def test_unclosed_block_comment_raises():
    with pytest.raises(ValueError):
        jsonc.loads('{"a": 1 /* sin cerrar }')


def test_invalid_json_raises():
    with pytest.raises(ValueError):
        jsonc.loads("{no es json}")
