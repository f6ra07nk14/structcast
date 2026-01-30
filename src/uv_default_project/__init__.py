"""Example module for the uv-default-project."""


def greet(name: str, formal: bool = False) -> str:
    """
    Generate a greeting message.

    Args:
        name: The name to greet
        formal: If True, use formal greeting format

    Returns:
        A greeting message
    """
    if formal:
        return f"Good day, {name}. Welcome!"
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """
    Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    return a + b


def mul(a: int, b: int) -> int:
    """
    Multiply two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    return a * b
