"""Reference solution for the Erdos Turán problem.

Uses the base-3 construction: integers in {1, ..., M} whose base-3
representation contains no digit '2'. This set is 3-AP-free by a
digit-by-digit argument and contains exactly 2047 elements for M=131072.

Expected: set_size=2047, score≈55.8.
"""


def solve(m: int) -> list[int]:
    result = []
    for x in range(1, m + 1):
        n = x
        valid = True
        while n > 0:
            if n % 3 == 2:
                valid = False
                break
            n //= 3
        if valid:
            result.append(x)
    return result
