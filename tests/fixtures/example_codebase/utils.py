"""
A simple Python library for testing the repository analyzer.
"""


class Calculator:
    """
    A simple calculator class with basic arithmetic operations.
    """

    def add(self, a, b):
        """
        Add two numbers.

        Args:
            a (float): First number
            b (float): Second number

        Returns:
            float: Sum of a and b
        """
        return a + b

    def subtract(self, a, b):
        """
        Subtract b from a.

        Args:
            a (float): First number
            b (float): Second number

        Returns:
            float: Difference of a and b
        """
        return a - b

    def multiply(self, a, b):
        """
        Multiply two numbers.

        Args:
            a (float): First number
            b (float): Second number

        Returns:
            float: Product of a and b
        """
        return a * b

    def divide(self, a, b):
        """
        Divide a by b.

        Args:
            a (float): Numerator
            b (float): Denominator

        Returns:
            float: Quotient of a and b

        Raises:
            ZeroDivisionError: If b is zero
        """
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b


class StringUtils:
    """
    Utility functions for string manipulation.
    """

    @staticmethod
    def reverse(text):
        """
        Reverse a string.

        Args:
            text (str): Input string

        Returns:
            str: Reversed string
        """
        return text[::-1]

    @staticmethod
    def count_words(text):
        """
        Count words in a string.

        Args:
            text (str): Input string

        Returns:
            int: Number of words
        """
        if not text:
            return 0
        return len(text.split())

    @staticmethod
    def to_uppercase(text):
        """
        Convert string to uppercase.

        Args:
            text (str): Input string

        Returns:
            str: Uppercase string
        """
        return text.upper()

    @staticmethod
    def to_lowercase(text):
        """
        Convert string to lowercase.

        Args:
            text (str): Input string

        Returns:
            str: Lowercase string
        """
        return text.lower()
