import os
import re
import tarfile
import struct
import ast
from typing import Dict, Optional, Iterable, Tuple, List


class _SafeExprEval:
    __slots__ = ("defines", "cache", "visiting")

    def __init__(self, defines: Dict[str, str]):
        self.defines = defines
        self.cache: Dict[str, Optional[int]] = {}
        self.visiting = set()

    @staticmethod
    def _strip_comments(s: str) -> str:
        s = s.split("//", 1)[0]
        s = s.split("/*", 1)[0]
        return s

    @staticmethod
    def _strip_casts(s: str) -> str:
        # Repeatedly remove leading casts like (guint16), (unsigned int), (const guint8 *)
        prev = None
        while prev != s:
            prev = s
            s = re.sub(r'^\s*\(\s*[A-Za-z_][A-Za-z0-9_\s\*]*\s*\)\s*', '', s)
        return s

    @staticmethod
    def _normalize_int_literals(s: str) -> str:
        # Remove common integer suffixes and wrappers not understood by Python
        s = re.sub(r'\b(UINT(?:8|16|32|64)_C)\s*\(', '(', s)
        s = re.sub(r'\bG_GUINT64_CONSTANT\s*\(', '(', s)
        s = re.sub(r'\bG_GUINT32_CONSTANT\s*\(', '(', s)
        s = re.sub(r'\bG_GUINT16_CONSTANT\s*\(', '(', s)
        s = re.sub(r'\bG_GUINT8_CONSTANT\s*\(', '(', s)

        # Strip suffixes like U, UL, LL
        s = re.sub(r'(?<=\b0x[0-9A-Fa-f]+)[uUlL]+', '', s)
        s = re.sub(r'(?<=\b[0-9]+)[uUlL]+', '', s)
        return s

    def _eval_ast(self, node: ast.AST, depth: int = 0) -> int:
        if depth > 40:
            raise ValueError("expr too deep")

        if isinstance(node, ast.Expression):
            return self._eval_ast(node.body, depth + 1)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return int(node.value)
            if isinstance(node.value, (int,)):
                return int(node.value)
            raise ValueError("unsupported constant")

        if isinstance(node, ast.Num):  # pragma: no cover
            return int(node.n)

        if isinstance(node, ast.BinOp):
            left = self._eval_ast(node.left, depth + 1)
            right = self._eval_ast(node.right, depth + 1)
            op = node.op
            if isinstance(op, ast.BitOr):
                return left | right
            if isinstance(op, ast.BitAnd):
                return left & right
            if isinstance(op, ast.BitXor):
                return left ^ right
            if isinstance(op, ast.LShift):
                return left << right
            if isinstance(op, ast.RShift):
                return left >> right
            if isinstance(op, ast.Add):
                return left + right
            if isinstance(op, ast.Sub):
                return left - right
            if isinstance(op, ast.Mult):
                return left * right
            if isinstance(op, (ast.Div, ast.FloorDiv)):
                if right == 0:
                    raise ValueError("div by zero")
                return left // right
            if isinstance(op, ast.Mod):
                if right == 0:
                    raise ValueError("mod by zero")
                return left % right
            raise ValueError("unsupported binop")

        if isinstance(node, ast.UnaryOp):
            val = self._eval_ast(node.operand, depth + 1)
            if isinstance(node.op, ast.Invert):
                return ~val
            if isinstance(node.op, ast.UAdd):
                return +val
            if isinstance(node.op, ast.USub):
                return -val
            raise ValueError("unsupported unaryop")

        if isinstance(node, ast.Name):
            v = self.resolve(node.id)
            if v is None:
                raise ValueError("unknown name")
            return v

        if isinstance(node, ast.ParenExpr):  # pragma: no cover
            return self._eval_ast(node.value, depth + 1)

        raise ValueError("unsupported node")

    def resolve(self, name: str) -> Optional[int]:
        if name in self.cache:
            return self.cache[name]
        if name in self.visiting:
            self.cache[name] = None
            return None
        expr = self.defines.get(name)
        if expr is None:
            self.cache[name] = None
            return None

        self.visiting.add(name)
        try:
            s = self._strip_comments(expr).strip()
            if not s:
                self.cache[name] = None
                return None
            s = self._strip_casts(s)
            s = self._normalize_int_literals(s)

            # Drop surrounding parentheses
            while True:
                st = s.strip()
                if st.startswith("(") and st.endswith(")"):
                    inner = st[1:-1].strip()
                    if inner.count("(") == inner.count(")"):
                        s = inner
                        continue
                break

            # If it is a simple hex/dec literal
            m = re.fullmatch(r'\s*(0x[0-9A-Fa-f]+|\d+)\s*', s)
            if m:
                val = int(m.group(1), 0)
                self.cache[name] = val
                return val

            # If it is a simple alias
            m = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*', s)
            if m:
                val = self.resolve(m.group(1))
                self.cache[name] = val
                return val

            # Try AST evaluation
            try:
                tree = ast.parse(s, mode="eval")
                val = self._eval_ast(tree)
                self.cache[name] = val
                return val
            except Exception:
                # Fallback: first hex/dec constant in expression
                m = re.search(r'(0x[0-9A-Fa-f]+|\b\d+\b)', s)
                if m:
                    val = int(m.group(1), 0)
                    self.cache[name] = val
                    return val
                self.cache[name] = None
                return None
        finally:
            self.visiting.discard(name)


def _pcap_global_header(linktype: int) -> bytes:
    # Little-endian pcap, magic 0xa1b2c3d4
    return struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 0xFFFF, linktype)


def _pcap_record(pkt: bytes, ts_sec: int = 0, ts_usec: int = 0) -> bytes:
    return struct.pack("<IIII", ts_sec, ts_usec, len(pkt), len(pkt)) + pkt


def _ipv4_checksum(hdr: bytes) -> int:
    if len(hdr) % 2 == 1:
        hdr += b"\x00"
    s = 0
    for i in range(0, len(hdr), 2):
        s += (hdr[i] << 8) | hdr[i + 1]
        s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _build_ipv4_gre_packet(gre_payload: bytes, src_ip: bytes = b"\x01\x01\x01\x01", dst_ip: bytes = b"\x02\x02\x02\x02") -> bytes:
    total_len = 20 + len(gre_payload)
    ver_ihl = 0x45
    tos = 0
    identification = 0
    flags_frag = 0
    ttl = 64
    proto = 47  # GRE
    checksum = 0
    ip_hdr = struct.pack(">BBHHHBBH4s4s", ver_ihl, tos, total_len, identification, flags_frag, ttl, proto, checksum, src_ip, dst_ip)
    checksum = _ipv4_checksum(ip_hdr)
    ip_hdr = struct.pack(">BBHHHBBH4s4s", ver_ihl, tos, total_len, identification, flags_frag, ttl, proto, checksum, src_ip, dst_ip)
    return ip_hdr + gre_payload


def _build_ether_ipv4_payload(ip_payload: bytes) -> bytes:
    dst = b"\x00\x00\x00\x00\x00\x00"
    src = b"\x00\x00\x00\x00\x00\x00"
    ethertype = b"\x08\x00"  # IPv4
    return dst + src + ethertype + ip_payload


def _build_gre_packet(proto_type: int, inner: bytes, flags_ver: int = 0x0000) -> bytes:
    return struct.pack(">HH", flags_ver & 0xFFFF, proto_type & 0xFFFF) + inner


def _iter_files_from_tar(src_path: str) -> Iterable[Tuple[str, bytes]]:
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            # Avoid huge non-source files
            if m.size > 8 * 1024 * 1024:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            finally:
                f.close()
            yield m.name, data


def _iter_files_from_dir(src_dir: str) -> Iterable[Tuple[str, bytes]]:
    for root, _, files in os.walk(src_dir):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size > 8 * 1024 * 1024:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            rel = os.path.relpath(path, src_dir)
            yield rel, data


def _iter_source_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        return _iter_files_from_dir(src_path)
    return _iter_files_from_tar(src_path)


def _decode_text(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_gre_proto_tokens(src_path: str) -> List[str]:
    tokens: List[str] = []
    gre_files: List[Tuple[str, bytes]] = []
    all_files: List[Tuple[str, bytes]] = []

    for name, data in _iter_source_files(src_path):
        lname = name.lower()
        if lname.endswith(".c") or lname.endswith(".cc") or lname.endswith(".cpp"):
            if "packet-gre" in os.path.basename(lname):
                gre_files.append((name, data))
        all_files.append((name, data))

    def scan_text(text: str):
        nonlocal tokens
        if "gre.proto" not in text:
            return
        for m in re.finditer(r'dissector_add_uint(?:_with_preference)?\s*\(\s*"gre\.proto"\s*,\s*([^,]+)\s*,\s*([^)]+)\)', text):
            whole = m.group(0).lower()
            arg1 = m.group(1).strip()
            arg2 = m.group(2).strip().lower()
            if ("802" in whole) or ("wlan" in whole) or ("ieee" in whole) or ("802" in arg1.lower()) or ("wlan" in arg2) or ("ieee" in arg2):
                tokens.append(arg1)

        # Additional patterns
        for m in re.finditer(r'("gre\.proto")', text):
            start = max(0, m.start() - 200)
            end = min(len(text), m.end() + 200)
            chunk = text[start:end].lower()
            if ("wlan" in chunk) or ("802" in chunk) or ("ieee" in chunk):
                # Try capture numeric/define after gre.proto within chunk
                m2 = re.search(r'gre\.proto"\s*,\s*([^,)\s]+)', text[start:end])
                if m2:
                    tokens.append(m2.group(1).strip())

    for name, data in gre_files:
        scan_text(_decode_text(data))

    if not tokens:
        # Fallback: scan all C/C++ sources quickly
        for name, data in all_files:
            lname = name.lower()
            if not (lname.endswith(".c") or lname.endswith(".cc") or lname.endswith(".cpp")):
                continue
            txt = _decode_text(data)
            if "gre.proto" in txt:
                scan_text(txt)

    # Dedup preserve order
    seen = set()
    out = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _collect_defines(src_path: str) -> Dict[str, str]:
    defines: Dict[str, str] = {}
    for name, data in _iter_source_files(src_path):
        lname = name.lower()
        if not (lname.endswith(".h") or lname.endswith(".c") or lname.endswith(".cc") or lname.endswith(".cpp")):
            continue
        text = _decode_text(data)
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.match(r'^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b(.*)$', line)
            if not m:
                i += 1
                continue
            macro = m.group(1)
            rest = m.group(2) if m.group(2) is not None else ""
            # Skip function-like macros (e.g., #define FOO(x) ...)
            if rest.lstrip().startswith("("):
                i += 1
                continue

            val = rest.strip()
            # handle multiline define with trailing backslash
            while val.endswith("\\") and i + 1 < len(lines):
                val = val[:-1].rstrip() + " " + lines[i + 1].rstrip()
                i += 1
            val = val.strip()
            if val:
                if macro not in defines:
                    defines[macro] = val
            i += 1
    return defines


def _parse_int_token(token: str, evaluator: Optional[_SafeExprEval] = None) -> Optional[int]:
    tok = token.strip()
    if not tok:
        return None
    tok = re.sub(r'^\((?:[^()]*?)\)\s*', '', tok).strip()  # remove simple leading cast
    tok = tok.strip()
    tok = tok.rstrip(");,")
    tok = tok.strip()
    tok = re.sub(r'\s+', '', tok)
    # If it's like "0x1234"
    if re.fullmatch(r'0x[0-9A-Fa-f]+', tok):
        return int(tok, 16)
    if re.fullmatch(r'\d+', tok):
        return int(tok, 10)
    # Might be wrapped in parentheses or with suffix
    tok2 = tok
    tok2 = re.sub(r'(?<=\b0x[0-9A-Fa-f]+)[uUlL]+', '', tok2)
    tok2 = re.sub(r'(?<=\b\d+)[uUlL]+', '', tok2)
    if re.fullmatch(r'0x[0-9A-Fa-f]+', tok2):
        return int(tok2, 16)
    if re.fullmatch(r'\d+', tok2):
        return int(tok2, 10)
    if evaluator is not None:
        v = evaluator.resolve(tok2)
        if v is not None:
            return v
    return None


def _find_linktype_gre(src_path: str, defines: Optional[Dict[str, str]] = None) -> Optional[int]:
    if defines is None:
        defines = _collect_defines(src_path)
    ev = _SafeExprEval(defines)

    # Prefer explicit LINKTYPE_GRE
    for k in ("LINKTYPE_GRE", "DLT_GRE"):
        v = ev.resolve(k)
        if v is not None and 0 <= v <= 0xFFFFFFFF:
            return v

    # Try to find mapping lines referencing WTAP_ENCAP_GRE to numeric linktype.
    # Scan sources for patterns like "{ 778, WTAP_ENCAP_GRE }" or "case 778: ... WTAP_ENCAP_GRE"
    for name, data in _iter_source_files(src_path):
        lname = name.lower()
        if not (lname.endswith(".c") or lname.endswith(".h")):
            continue
        text = _decode_text(data)
        if "WTAP_ENCAP_GRE" not in text:
            continue
        m = re.search(r'\{\s*(\d+)\s*,\s*WTAP_ENCAP_GRE\s*\}', text)
        if m:
            return int(m.group(1))
        m = re.search(r'case\s+(\d+)\s*:\s*(?:.|\n){0,200}?WTAP_ENCAP_GRE', text)
        if m:
            return int(m.group(1))

    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        tokens = _extract_gre_proto_tokens(src_path)

        defines = None
        evaluator = None

        proto_vals: List[int] = []
        for t in tokens:
            if re.search(r'[A-Za-z_]', t):
                if defines is None:
                    defines = _collect_defines(src_path)
                    evaluator = _SafeExprEval(defines)
                v = _parse_int_token(t, evaluator)
            else:
                v = _parse_int_token(t, None)
            if v is not None:
                v &= 0xFFFF
                if v not in proto_vals:
                    proto_vals.append(v)

        # Fallback: try resolve likely ethertype macro names
        if not proto_vals:
            if defines is None:
                defines = _collect_defines(src_path)
                evaluator = _SafeExprEval(defines)
            likely = [
                "ETHERTYPE_IEEE802_11",
                "ETHERTYPE_IEEE80211",
                "ETHERTYPE_IEEE_802_11",
                "ETHERTYPE_IEEE_802_11_RAW",
                "ETHERTYPE_IEEE802_11_RAW",
            ]
            for k in likely:
                v = evaluator.resolve(k)
                if v is not None:
                    v &= 0xFFFF
                    if v not in proto_vals:
                        proto_vals.append(v)

        # Another fallback: scan defines for keys containing IEEE and 802 and 11 and ETHERTYPE
        if not proto_vals:
            if defines is None:
                defines = _collect_defines(src_path)
            evaluator = _SafeExprEval(defines)
            candidates: List[int] = []
            for k in defines.keys():
                lk = k.lower()
                if "ethertype" in lk and "802" in lk and "11" in lk and ("ieee" in lk or "wlan" in lk):
                    v = evaluator.resolve(k)
                    if v is not None:
                        v &= 0xFFFF
                        if 0 <= v <= 0xFFFF:
                            candidates.append(v)
            for v in candidates:
                if v not in proto_vals:
                    proto_vals.append(v)

        # Absolute last-resort candidates (unlikely needed)
        if not proto_vals:
            proto_vals = [0x0019, 0x0017, 0x0080, 0x88BF]

        # Choose linktype: prefer GRE if discoverable, else Ethernet
        if defines is None:
            defines = _collect_defines(src_path)
        linktype_gre = _find_linktype_gre(src_path, defines=defines)
        use_gre_linktype = linktype_gre is not None and 0 <= linktype_gre <= 0xFFFFFFFF

        # Minimal 802.11 payload (2 bytes frame control)
        inner_80211 = b"\x00\x00"

        records = []
        if use_gre_linktype:
            gh = _pcap_global_header(int(linktype_gre))
            for pv in proto_vals[:3]:
                gre = _build_gre_packet(pv, inner_80211)
                records.append(_pcap_record(gre))
            return gh + b"".join(records)

        # Ethernet fallback: Ethernet + IPv4 + GRE + 802.11
        gh = _pcap_global_header(1)
        for pv in proto_vals[:3]:
            gre = _build_gre_packet(pv, inner_80211)
            ip = _build_ipv4_gre_packet(gre)
            eth = _build_ether_ipv4_payload(ip)
            records.append(_pcap_record(eth))
        return gh + b"".join(records)