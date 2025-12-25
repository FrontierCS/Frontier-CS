class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
        deflate = b'\x03\x80\x01\x00\x00\x00\x00\x00\x00'
        trailer = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        return header + deflate + trailer
