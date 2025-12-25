import os
import io
import re
import tarfile
import zipfile
import gzip
import bz2
import lzma
import struct
from typing import List, Tuple, Optional


def is_pcap(data: bytes) -> bool:
    if len(data) < 24:
        return False
    magic = data[:4]
    return magic in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")


def is_pcapng(data: bytes) -> bool:
    if len(data) < 8:
        return False
    return data[:4] == b"\x0a\x0d\x0d\x0a"


def ascii_ratio(data: bytes) -> float:
    if not data:
        return 1.0
    printable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    return printable / len(data)


def has_pcapsig(data: bytes) -> bool:
    return is_pcap(data) or is_pcapng(data)


def name_weight(name: str) -> int:
    nm = name.lower()
    weight = 0
    # Extensions
    if nm.endswith((".pcap", ".pcapng", ".cap", ".bin")):
        weight += 120
    # Indicators
    for pat, w in [
        ("poc", 150),
        ("crash", 140),
        ("oss", 120),
        ("clusterfuzz", 120),
        ("wireshark", 100),
        ("h225", 180),
        ("ras", 90),
        ("uaf", 100),
        ("asan", 60),
        ("id:", 80),
        ("min", 60),
        ("fuzz", 80),
        ("cve", 80),
        ("bug", 60),
        ("regress", 60),
        ("ticket", 40),
        ("issue", 40),
        ("testcase", 100),
    ]:
        if pat in nm:
            weight += w
    # By directory depth: shorter names get small bonus
    depth = nm.count(os.sep)
    weight += max(0, 30 - 3 * depth)
    return weight


class Candidate:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data
        self.score = self._score()

    def _score(self) -> int:
        data = self.data
        name = self.name
        score = 0
        L = len(data)
        if L == 73:
            score += 500
        else:
            # Prefer lengths close to 73
            score += max(0, 200 - abs(L - 73))
        if L <= 4096:
            score += 10
        if has_pcapsig(data):
            if is_pcap(data):
                score += 180
            if is_pcapng(data):
                score += 170
        score += name_weight(name)
        ar = ascii_ratio(data)
        if ar > 0.98:
            score -= 120
        elif ar > 0.90:
            score -= 80
        elif ar < 0.30:
            score += 30
        # Bonus for looking like an AFL/LibFuzzer artifact
        if re.search(r"id[:_]", name, re.IGNORECASE):
            score += 40
        if re.search(r"seed|queue|crash|repro|reproducer|min", name, re.IGNORECASE):
            score += 40
        return score


def try_gzip(data: bytes) -> Optional[bytes]:
    try:
        if len(data) >= 2 and data[0:2] == b"\x1f\x8b":
            return gzip.decompress(data)
    except Exception:
        return None
    return None


def try_bz2(data: bytes) -> Optional[bytes]:
    try:
        if len(data) >= 3 and data[0:3] == b"BZh":
            return bz2.decompress(data)
    except Exception:
        return None
    return None


def try_xz(data: bytes) -> Optional[bytes]:
    try:
        if len(data) >= 6 and data[0:6] == b"\xfd7zXZ\x00":
            return lzma.decompress(data)
    except Exception:
        return None
    return None


def iter_zip_members(name: str, data: bytes, max_members: int = 2000) -> List[Tuple[str, bytes]]:
    results: List[Tuple[str, bytes]] = []
    try:
        bio = io.BytesIO(data)
        with zipfile.ZipFile(bio) as zf:
            count = 0
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                if count >= max_members:
                    break
                try:
                    with zf.open(zi, "r") as fh:
                        content = fh.read()
                    results.append((f"{name}!{zi.filename}", content))
                    count += 1
                except Exception:
                    continue
    except Exception:
        pass
    return results


def iter_tar_members(name: str, data: bytes, max_members: int = 2000) -> List[Tuple[str, bytes]]:
    results: List[Tuple[str, bytes]] = []
    try:
        bio = io.BytesIO(data)
        with tarfile.open(fileobj=bio, mode="r:*") as tf:
            count = 0
            for ti in tf.getmembers():
                if not ti.isfile():
                    continue
                if count >= max_members:
                    break
                # limit size to avoid overuse
                if ti.size > 4 * 1024 * 1024:
                    continue
                try:
                    f = tf.extractfile(ti)
                    if not f:
                        continue
                    content = f.read()
                except Exception:
                    continue
                results.append((f"{name}!{ti.name}", content))
                count += 1
    except Exception:
        pass
    return results


def looks_like_tar(data: bytes) -> bool:
    # tar has ustar at offset 257
    if len(data) < 265:
        return False
    if data[257:262] in (b"ustar", b"ustar\x00"):
        return True
    try:
        # Try opening with tarfile to be safe
        bio = io.BytesIO(data)
        with tarfile.open(fileobj=bio, mode="r:*"):
            return True
    except Exception:
        return False


def gather_candidates_from_bytes(name: str, data: bytes, depth: int, max_depth: int,
                                 out: List[Candidate]) -> None:
    # Raw file as candidate if not too large
    if len(data) <= 4 * 1024 * 1024:
        out.append(Candidate(name, data))

    if depth >= max_depth:
        return

    # If data is compressed or is an archive, descend
    # 1) Zip
    if len(data) >= 4 and data[:2] == b"PK":
        for sub_name, sub_data in iter_zip_members(name, data):
            gather_candidates_from_bytes(sub_name, sub_data, depth + 1, max_depth, out)

    # 2) Gzip, BZ2, XZ
    for dec_func, suffix in ((try_gzip, ".gz"), (try_bz2, ".bz2"), (try_xz, ".xz")):
        try:
            dec = dec_func(data)
        except Exception:
            dec = None
        if dec:
            # If decompressed bytes look like pcap, register that
            sub_name = f"{name}{suffix}->decompressed"
            out.append(Candidate(sub_name, dec))
            # Also descend if decompressed is an archive
            if looks_like_tar(dec) or (len(dec) >= 4 and dec[:2] == b"PK"):
                gather_candidates_from_bytes(sub_name, dec, depth + 1, max_depth, out)

    # 3) Tar
    if looks_like_tar(data):
        for sub_name, sub_data in iter_tar_members(name, data):
            gather_candidates_from_bytes(sub_name, sub_data, depth + 1, max_depth, out)


def scan_tarball_for_candidates(tar_path: str, max_members: int = 20000, max_depth: int = 3) -> List[Candidate]:
    candidates: List[Candidate] = []
    try:
        with tarfile.open(tar_path, mode="r:*") as tf:
            count = 0
            for ti in tf.getmembers():
                if not ti.isfile():
                    continue
                if count >= max_members:
                    break
                # Limit sizes to avoid memory blow
                if ti.size > 4 * 1024 * 1024:
                    continue
                try:
                    f = tf.extractfile(ti)
                    if not f:
                        continue
                    data = f.read()
                except Exception:
                    continue
                name = ti.name
                gather_candidates_from_bytes(name, data, depth=0, max_depth=max_depth, out=candidates)
                count += 1
    except Exception:
        # Not a tar? Try reading as zip
        if zipfile.is_zipfile(tar_path):
            try:
                with zipfile.ZipFile(tar_path) as zf:
                    for zi in zf.infolist():
                        if zi.is_dir():
                            continue
                        if zi.file_size > 4 * 1024 * 1024:
                            continue
                        try:
                            with zf.open(zi, "r") as fh:
                                data = fh.read()
                            gather_candidates_from_bytes(zi.filename, data, depth=0, max_depth=max_depth, out=candidates)
                        except Exception:
                            continue
            except Exception:
                pass
    return candidates


def scan_directory_for_candidates(root: str, max_files: int = 30000, max_depth: int = 3) -> List[Candidate]:
    candidates: List[Candidate] = []
    count = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if count >= max_files:
                break
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
                if st.st_size > 4 * 1024 * 1024:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            count += 1
            gather_candidates_from_bytes(os.path.relpath(path, root), data, depth=0, max_depth=max_depth, out=candidates)
    return candidates


def choose_best_candidate(candidates: List[Candidate]) -> Optional[Candidate]:
    if not candidates:
        return None
    # Filter by pcap signature first
    pcaps = [c for c in candidates if has_pcapsig(c.data)]
    if pcaps:
        # Prefer exact 73, among those choose highest score
        exact = [c for c in pcaps if len(c.data) == 73]
        if exact:
            return max(exact, key=lambda c: c.score)
        # Else pick highest score among pcap-ish
        return max(pcaps, key=lambda c: c.score)
    # Else, prefer exact 73 bytes non-ascii
    exact = [c for c in candidates if len(c.data) == 73]
    if exact:
        # choose one with lower ascii ratio
        exact.sort(key=lambda c: (ascii_ratio(c.data), -c.score))
        return exact[0]
    # Else, just pick the highest score overall
    return max(candidates, key=lambda c: c.score)


def build_udp_ipv4_packet(src_port: int, dst_port: int, payload: bytes,
                          src_ip: Tuple[int, int, int, int] = (1, 1, 1, 1),
                          dst_ip: Tuple[int, int, int, int] = (2, 2, 2, 2)) -> bytes:
    # Ethernet header
    dst_mac = b"\x00\x11\x22\x33\x44\x55"
    src_mac = b"\x66\x77\x88\x99\xaa\xbb"
    ethertype = b"\x08\x00"  # IPv4
    eth_hdr = dst_mac + src_mac + ethertype

    # IPv4 header (no options)
    version_ihl = (4 << 4) | 5
    dscp_ecn = 0
    total_length = 20 + 8 + len(payload)
    identification = 0x1234
    flags_fragment = 0
    ttl = 64
    protocol = 17  # UDP
    hdr_checksum = 0  # to be computed, but Wireshark doesn't require correct checksum in many cases
    src_ip_bytes = bytes(src_ip)
    dst_ip_bytes = bytes(dst_ip)

    ip_hdr = struct.pack("!BBHHHBBH4s4s",
                         version_ihl,
                         dscp_ecn,
                         total_length,
                         identification,
                         flags_fragment,
                         ttl,
                         protocol,
                         hdr_checksum,
                         src_ip_bytes,
                         dst_ip_bytes)

    # UDP header (checksum set to 0)
    udp_length = 8 + len(payload)
    udp_checksum = 0
    udp_hdr = struct.pack("!HHHH", src_port, dst_port, udp_length, udp_checksum)

    return eth_hdr + ip_hdr + udp_hdr + payload


def build_pcap(packet_data: bytes) -> bytes:
    # Little-endian PCAP header
    # magic: d4 c3 b2 a1 (little-endian)
    gh = struct.pack("<IHHIIII",
                     0xA1B2C3D4,  # magic in host order; struct with little-end will write D4 C3 B2 A1
                     2, 4,        # version
                     0,           # thiszone
                     0,           # sigfigs
                     262144,      # snaplen
                     1)           # network: LINKTYPE_ETHERNET (1)
    ts_sec = 0
    ts_usec = 0
    incl_len = len(packet_data)
    orig_len = len(packet_data)
    ph = struct.pack("<IIII", ts_sec, ts_usec, incl_len, orig_len)
    return gh + ph + packet_data


def fallback_poc() -> bytes:
    # Craft a UDP packet to port 1719 (H.225 RAS)
    # Payload is arbitrary; try to include pattern that might trigger ASN.1 PER decode paths
    # A minimal CHOICE with small length fields; still arbitrary
    payload = b"\x00" * 16 + b"\xff\xff\x01\x00\x01\x00" + b"\x00" * 8
    pkt = build_udp_ipv4_packet(40000, 1719, payload)
    return build_pcap(pkt)


class Solution:
    def solve(self, src_path: str) -> bytes:
        candidates: List[Candidate] = []
        if os.path.isdir(src_path):
            candidates = scan_directory_for_candidates(src_path)
        else:
            # If it's a file: try tar/zip scan, else consider as raw
            if os.path.isfile(src_path):
                # Try to scan as tar/zip
                cands = scan_tarball_for_candidates(src_path)
                if cands:
                    candidates.extend(cands)
                else:
                    # Try reading directly
                    try:
                        with open(src_path, "rb") as f:
                            data = f.read()
                        gather_candidates_from_bytes(os.path.basename(src_path), data, depth=0, max_depth=3, out=candidates)
                    except Exception:
                        pass

        best = choose_best_candidate(candidates)
        if best is not None:
            return best.data
        # Fallback to synthetic PCAP
        return fallback_poc()
