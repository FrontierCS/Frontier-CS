import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal gzip file with a single fixed-Huffman block containing only
        # an end-of-block symbol (no uncompressed data). This triggers the
        # Huffman decoding in upng-gzip.
        return b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00"
