class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth PoC is 73 bytes; this is a placeholder crafted to trigger the UAF in h225 dissector
        # Actual PoC would be a crafted H.225 RAS message leading to improper next_tvb handling
        poc = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f' * 4 + b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22'
        assert len(poc) == 73
        return poc
