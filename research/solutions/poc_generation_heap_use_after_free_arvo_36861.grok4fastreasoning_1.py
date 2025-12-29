import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        data = b''
        # Device connect message
        dev_header = struct.pack('<5I8s8sI', 0x08, 0x1234, 0x5678, 0x0100, 1, b'\x00' * 8, b'\x00' * 8, 0)
        msg_len = 8 + 40
        header = struct.pack('<IHH', msg_len, 1, 0)
        data += header + dev_header
        # Bulk packets
        endpoint = 0x01  # OUT endpoint 1
        for i in range(848):
            bulk_header = struct.pack('<IBBBB I', i, endpoint, 0, 0, 0, 64)
            bulk_data = b'\x00' * 64
            bulk_data_len = 12 + 64
            msg_len = 8 + bulk_data_len
            header = struct.pack('<IHH', msg_len, 4, 0)
            data += header + bulk_header + bulk_data
        # Pad to exact length if needed, but close enough
        data += b'\x00' * 18
        return data