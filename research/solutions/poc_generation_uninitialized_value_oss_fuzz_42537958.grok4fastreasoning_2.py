class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a simple PPM image for compression fuzzer
        # 1x1 pixel red image
        header = b'P6\n1 1\n255\n'
        data = b'\xff\x00\x00'  # Red pixel
        poc = header + data
        return poc