import typing

class Solution:
    def solve(self, src_path: str) -> bytes:
        field_len = 48
        payload = b"0" * field_len + b" " + b"0" * field_len + b" n\n"
        return payload