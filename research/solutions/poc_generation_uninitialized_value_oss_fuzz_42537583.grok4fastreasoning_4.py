import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        len_data = 1021
        header = struct.pack('>I', len_data)
        data = b'\xff\xd8' + b'\x00' * 1019
        return header + data