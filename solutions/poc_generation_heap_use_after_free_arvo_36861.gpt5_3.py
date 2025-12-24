import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a large input to ensure serializer buffer reallocation (>64kB)
        # Use newline-delimited chunks to be robust against potential line-based splitting in harnesses.
        chunk = b'A' * 1023 + b'\n'  # 1024 bytes per chunk, no NUL bytes
        return chunk * 100  # 102,400 bytes total
