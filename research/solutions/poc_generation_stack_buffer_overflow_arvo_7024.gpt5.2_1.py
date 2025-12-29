import os
import re
import tarfile
import struct
import ast
from typing import Dict, Iterator, List, Optional, Tuple


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        yield p, f.read()
                except OSError:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0:
                    continue
                if m.size > 8_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                yield m.name, data
    except Exception:
        # If it's not a tarball, treat as a regular file tree root fallback
        return


_num_lit_re = re.compile(r"^\s*\(?\s*(0x[0-9A-Fa-f]+|\d+)\s*\)?\s*([uUlL]{0,3})\s*$")
_define_re = re.compile(
    r"(?m)^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+\(?\s*(0x[0-9A-Fa-f]+|\d+)\s*\)?\s*([uUlL]{0,3})\b"
)
_enum_assign_re = re.compile(
    r"(?m)\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(?\s*(0x[0-9A-Fa-f]+|\d+)\s*\)?\s*([uUlL]{0,3})\b"
)


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


def _parse_int_literal(s: str) -> Optional[int]:
    m = _num_lit_re.match(s)
    if not m:
        return None
    v = m.group(1)
    try:
        if v.lower().startswith("0x"):
            return int(v, 16)
        return int(v, 10)
    except Exception:
        return None


def _is_balanced_parens(s: str) -> bool:
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _has_top_level_comma(s: str) -> bool:
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            return True
    return False


_WRAPPERS = {
    "G_GUINT16_TO_BE",
    "G_GUINT16_TO_LE",
    "GUINT16_TO_BE",
    "GUINT16_TO_LE",
    "GUINT16_SWAP_LE_BE",
    "GUINT16_SWAP_BE_LE",
    "g_htons",
    "htons",
    "pntoh16",
    "pntohs",
    "ntohs",
    "tvb_get_ntohs",
    "tvb_get_guint16",
    "tvb_get_ntohs_offset",
}


def _unwrap_expr(expr: str) -> str:
    e = expr.strip()
    e = _strip_c_comments(e).strip()
    # Strip leading casts: (type)expr
    for _ in range(4):
        m = re.match(r"^\(\s*([A-Za-z_][A-Za-z0-9_\s\*]*)\s*\)\s*(.+)$", e, flags=re.S)
        if not m:
            break
        type_part = m.group(1)
        rest = m.group(2).strip()
        if re.search(r"[0-9\+\-\|\&\^\<\>\/\%]", type_part):
            break
        e = rest

    # Strip simple wrappers and redundant parentheses
    for _ in range(12):
        e2 = e.strip()
        if e2.startswith("(") and e2.endswith(")") and _is_balanced_parens(e2[1:-1]):
            inner = e2[1:-1].strip()
            e = inner
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$", e2, flags=re.S)
        if m:
            fn = m.group(1)
            inside = m.group(2).strip()
            if fn in _WRAPPERS and _is_balanced_parens(inside) and not _has_top_level_comma(inside):
                e = inside
                continue
        break
    return e.strip()


class _SafeEval(ast.NodeVisitor):
    def visit(self, node):
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, int):
            return node.value
        raise ValueError("non-int constant")

    def visit_Num(self, node: ast.Num):
        if isinstance(node.n, int):
            return node.n
        raise ValueError("non-int num")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        v = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +v
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.Invert):
            return ~v
        raise ValueError("bad unary op")

    def visit_BinOp(self, node: ast.BinOp):
        l = self.visit(node.left)
        r = self.visit(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return l + r
        if isinstance(op, ast.Sub):
            return l - r
        if isinstance(op, ast.Mult):
            return l * r
        if isinstance(op, ast.FloorDiv):
            return l // r
        if isinstance(op, ast.Mod):
            return l % r
        if isinstance(op, ast.BitOr):
            return l | r
        if isinstance(op, ast.BitAnd):
            return l & r
        if isinstance(op, ast.BitXor):
            return l ^ r
        if isinstance(op, ast.LShift):
            return l << r
        if isinstance(op, ast.RShift):
            return l >> r
        raise ValueError("bad binop")

    def generic_visit(self, node):
        raise ValueError(f"disallowed node: {type(node).__name__}")


def _resolve_expr(expr: str, const_map: Dict[str, int]) -> Optional[int]:
    e = _unwrap_expr(expr)
    lit = _parse_int_literal(e)
    if lit is not None:
        return lit
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", e):
        return const_map.get(e)

    def repl(m: re.Match) -> str:
        name = m.group(0)
        if name in const_map:
            return str(const_map[name])
        return name

    e2 = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", repl, e)
    if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\b", e2):
        return None
    try:
        tree = ast.parse(e2, mode="eval")
        return int(_SafeEval().visit(tree))
    except Exception:
        return None


def _ipv4_checksum(hdr: bytes) -> int:
    if len(hdr) % 2:
        hdr += b"\x00"
    s = 0
    for i in range(0, len(hdr), 2):
        w = (hdr[i] << 8) + hdr[i + 1]
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _build_pcap_le(linktype: int, packet: bytes) -> bytes:
    gh = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, linktype & 0xFFFFFFFF)
    ph = struct.pack("<IIII", 0, 0, len(packet), len(packet))
    return gh + ph + packet


def _build_eth_ipv4_gre_packet(gre_ptype: int) -> bytes:
    eth = b"\x00\x01\x02\x03\x04\x05" + b"\x06\x07\x08\x09\x0a\x0b" + b"\x08\x00"
    payload = b"\x00"
    gre = struct.pack("!HH", 0x0000, gre_ptype & 0xFFFF) + payload
    total_len = 20 + len(gre)
    vihl = 0x45
    tos = 0
    ident = 0
    flags_frag = 0
    ttl = 64
    proto = 47
    csum = 0
    src = b"\x01\x01\x01\x01"
    dst = b"\x02\x02\x02\x02"
    ip_hdr = struct.pack("!BBHHHBBH4s4s", vihl, tos, total_len, ident, flags_frag, ttl, proto, csum, src, dst)
    csum = _ipv4_checksum(ip_hdr)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", vihl, tos, total_len, ident, flags_frag, ttl, proto, csum, src, dst)
    return eth + ip_hdr + gre


class Solution:
    def solve(self, src_path: str) -> bytes:
        const_map: Dict[str, int] = {}
        linktype_gre: Optional[int] = None
        gre_candidates: List[Tuple[int, str, str]] = []  # (score, expr, filename)

        add_uint_re = re.compile(
            r'dissector_add_uint(?:_with_preference)?\s*\(\s*"gre\.proto"\s*,\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)',
            flags=re.S,
        )

        for fname, data in _iter_source_files(src_path):
            lower = fname.lower()
            ext = os.path.splitext(lower)[1]

            if ext in (".h", ".c", ".cc", ".cpp", ".inc"):
                try:
                    text = data.decode("utf-8", "ignore")
                except Exception:
                    text = data.decode("latin-1", "ignore")

                for m in _define_re.finditer(text):
                    name = m.group(1)
                    val_s = m.group(2)
                    v = _parse_int_literal(val_s)
                    if v is not None and name not in const_map:
                        const_map[name] = v

                for m in _enum_assign_re.finditer(text):
                    name = m.group(1)
                    val_s = m.group(2)
                    v = _parse_int_literal(val_s)
                    if v is not None and name not in const_map:
                        const_map[name] = v

                if linktype_gre is None and (b"LINKTYPE_GRE" in data or b"DLT_GRE" in data):
                    m = re.search(r"(?m)^\s*#\s*define\s+LINKTYPE_GRE\s+(\d+)\b", text)
                    if m:
                        try:
                            linktype_gre = int(m.group(1))
                        except Exception:
                            pass
                    if linktype_gre is None:
                        m = re.search(r"(?m)^\s*#\s*define\s+DLT_GRE\s+(\d+)\b", text)
                        if m:
                            try:
                                linktype_gre = int(m.group(1))
                            except Exception:
                                pass
                    if linktype_gre is None:
                        m = re.search(r"case\s+(\d+)\s*:\s*/\*\s*LINKTYPE_GRE\s*\*/", text)
                        if m:
                            try:
                                linktype_gre = int(m.group(1))
                            except Exception:
                                pass
                    if linktype_gre is None:
                        m = re.search(r"case\s+(\d+)\s*:\s*/\*\s*DLT_GRE\s*\*/", text)
                        if m:
                            try:
                                linktype_gre = int(m.group(1))
                            except Exception:
                                pass

                if b"gre.proto" in data:
                    for m in add_uint_re.finditer(text):
                        expr = m.group(1).strip()
                        handle_expr = m.group(2)
                        s = 0
                        fl = fname.lower()
                        hl = handle_expr.lower()
                        el = expr.lower()
                        if "80211" in fl or "802_11" in fl or "ieee80211" in fl:
                            s += 10
                        if "80211" in hl or "802_11" in hl or "ieee80211" in hl:
                            s += 10
                        if "wlan" in hl:
                            s += 6
                        if "80211" in el or "802_11" in el:
                            s += 3
                        if "wlan" in fl:
                            s += 2
                        if s > 0:
                            gre_candidates.append((s, expr, fname))

        if linktype_gre is None:
            linktype_gre = const_map.get("LINKTYPE_GRE") or const_map.get("DLT_GRE")

        gre_ptype: Optional[int] = None
        if gre_candidates:
            gre_candidates.sort(key=lambda x: (-x[0], len(x[1])))
            for _, expr, _fname in gre_candidates[:10]:
                gre_ptype = _resolve_expr(expr, const_map)
                if gre_ptype is not None and 0 <= gre_ptype <= 0xFFFF:
                    break

        if gre_ptype is None:
            # Heuristic fallback: any constant name indicating 802.11 GRE protocol
            best_name = None
            for k in const_map.keys():
                kl = k.lower()
                if "gre" in kl and ("80211" in kl or "802_11" in kl or "ieee80211" in kl or "wlan" in kl):
                    best_name = k
                    break
            if best_name is not None:
                gre_ptype = const_map.get(best_name)

        if gre_ptype is None:
            # Last resort (unlikely to work if we can't find the mapping)
            gre_ptype = 0x6558  # Transparent Ethernet bridging

        # Prefer minimal: GRE linktype with minimal GRE header and 1 byte payload (total 5 bytes packet)
        if linktype_gre is not None and isinstance(linktype_gre, int) and linktype_gre > 0:
            pkt = struct.pack("!HH", 0x0000, gre_ptype & 0xFFFF) + b"\x00"
            return _build_pcap_le(linktype_gre, pkt)

        # Fallback: Ethernet/IPv4/GRE
        pkt = _build_eth_ipv4_gre_packet(gre_ptype)
        return _build_pcap_le(1, pkt)