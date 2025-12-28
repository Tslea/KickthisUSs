"""
Test Project - Simple Python Calculator
"""

def add(first_number, second_number):
    """Add two numbers"""
    return first_number + second_number

def subtract(first_number, second_number):
    """Subtract two numbers"""
    return first_number - second_number

def multiply(first_number, second_number):
    """Multiply two numbers"""
    return first_number * second_number

def divide(dividend, divisor):
    """Divide two numbers"""
    if divisor == 0:
        raise ValueError("Cannot divide by zero")
    return dividend / divisor

if __name__ == "__main__":
    print("Calculator Test")
    print(f"2 + 3 = {add(2, 3)}")
    print(f"5 - 2 = {subtract(5, 2)}")
    print(f"4 * 3 = {multiply(4, 3)}")
    print(f"10 / 2 = {divide(10, 2)}")
