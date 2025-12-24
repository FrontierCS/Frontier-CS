import math

def is_perfect_square(num):
    """
    Check if the given number is a perfect square.
    """
    if num < 0:
        return False
    root = int(math.sqrt(num))
    return root * root == num

# Example usage:
# print(is_perfect_square(16))  # True
# print(is_perfect_square(15))  # False
