class Solution:
    def solve(self, src_path: str) -> bytes:
        return bytes([0x65]) + b'GNU' + bytes([0x02, 21]) + b'012345678901234567890'
