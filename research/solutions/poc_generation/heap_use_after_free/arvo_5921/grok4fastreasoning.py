import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        ip_header = b'\x45\x00\x00\x21\x00\x01\x00\x00\x40\x11\x8b\xc9\x7f\x00\x00\x01\x7f\x00\x00\x01'
        udp_header = b'\x06\xb7\x06\xb7\x00\x0d\x00\x00'
        data = b'\x00\x00\x00\x00\x00'
        ip_packet = ip_header + udp_header + data
        global_header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 101)
        packet_header = struct.pack('<IIII', 0, 0, 33, 33)
        return global_header + packet_header + ip_packet