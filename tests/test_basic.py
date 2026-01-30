"""Tests for the uv-default-project."""

from uv_default_project import add, greet


def test_greet():
    """Test the greet function."""
    assert greet("Alice") == "Hello, Alice!"
    assert greet("World") == "Hello, World!"


def test_greet_formal():
    """Test the greet function with formal parameter."""
    assert greet("Alice", formal=True) == "Good day, Alice. Welcome!"
    assert greet("World", formal=False) == "Hello, World!"


def test_add():
    """Test the add function."""
    assert add(2, 3) == 5
    assert add(0, 0) == 0
    assert add(-1, 1) == 0
    assert add(10, -5) == 5
