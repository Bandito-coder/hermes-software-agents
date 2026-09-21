"""Tests for textutils."""

import pytest

from textutils import find_first, slugify, truncate, word_count


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Hello, World! Foo") == "hello-world-foo"

    def test_leading_trailing_hyphens(self):
        assert slugify("--hello--") == "hello"

    def test_empty(self):
        assert slugify("") == ""


class TestWordCount:
    def test_basic(self):
        assert word_count("one two three") == 3

    def test_empty(self):
        assert word_count("") == 0


class TestTruncate:
    def test_no_truncation(self):
        assert truncate("short", 10) == "short"

    def test_truncation(self):
        assert truncate("hello world", 8) == "hello w…"

    def test_suffix_only(self):
        assert truncate("hello", 1) == "…"


class TestFindFirst:
    def test_found(self):
        assert find_first("hello world", "world") == 6

    def test_not_found(self):
        assert find_first("hello", "xyz") is None
