"""Basic tests to verify test infrastructure works."""

import pytest


def test_truth():
    """Verify basic test execution works."""
    assert True


def test_math():
    """Verify pytest discovers and runs tests."""
    assert 1 + 1 == 2


def test_string():
    """Test string operations."""
    assert "hello".upper() == "HELLO"


class TestBasicOperations:
    """Test class for grouping related tests."""

    def test_addition(self):
        """Test addition operation."""
        assert 5 + 3 == 8

    def test_subtraction(self):
        """Test subtraction operation."""
        assert 10 - 4 == 6
