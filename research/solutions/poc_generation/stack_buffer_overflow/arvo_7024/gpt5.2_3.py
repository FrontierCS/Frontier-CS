import os
import re
import tarfile
import struct
import ast
from typing import Dict, Optional, Tuple, Iterable


def _strip_c_line_comment(s: str) -> str:
    s = re.sub(r'/\*.*?\*/', '', s)
    s = re.sub(r'//.*$', '', s)
    return s.strip()


def _collect_defines_and_enums_from_text(text: str, define_map: Dict[str, str], enum_map: Dict[str, int]) -> None:
    # Collect non-function-like #defines
    for m in re.finditer(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s*(.*)$', text, flags=re.M):
        name = m.group(1)
        rest = m.group(2) if m.group(2) is not None else ""
        if not rest:
            continue
        if name.endswith("_H") and rest == "1":
            # include guard; still ok but unimportant
            pass
        # ignore function-like macros
        if re.match(r'^\s*\(', rest):
            continue
        # ignore if looks like a function macro definition like "#define X(y) ..."
        # (We can't directly see "(y)" here since it's in name in preprocessor syntax, but allow safe filter)
        if re.search(r'\b' + re.escape(name) + r'\s*\(', m.group(0)):
            continue
        val = _strip_c_line_comment(rest)
        if not val:
            continue
        if any(ch.isdigit() for ch in val) or "0x" in val.lower() or re.search(r'\b[A-Za-z_]\w*\b', val):
            if name not in define_map:
                define_map[name] = val

    # Collect enum entries with explicit values
    for m in re.finditer(r'\b([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b', text):
        n = m.group(1)
        v = m.group(2)
        if n not in enum_map:
            try:
                enum_map[n] = int(v, 0)
            except Exception:
                pass


def _normalize_c_expr(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r'/\*.*?\*/', ' ', expr, flags=re.S)
    expr = re.sub(r'//.*', ' ', expr)
    expr = expr.replace('\r', ' ').replace('\n', ' ')
    expr = re.sub(r'\s+', ' ', expr)

    # Strip common integer suffixes: U, L, UL, ULL, etc.
    expr = re.sub(r'\b(0x[0-9A-Fa-f]+|\d+)\s*([uUlL]+)\b', r'\1', expr)

    # Remove common casts like (guint16), (unsigned int), (const guint8*), etc.
    # Best-effort; avoid removing parenthesized expressions by restricting to type-ish tokens.
    cast_pat = re.compile(
        r'\(\s*(?:const\s+)?(?:unsigned|signed)?\s*(?:long\s+long|long|short|int|char|void|size_t|ssize_t|gsize|gssize|guint|gint|gboolean|guint8|guint16|guint32|guint64|gint8|gint16|gint32|gint64|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t)\s*(?:\*+\s*)?\)'
    )
    for _ in range(8):
        new_expr = cast_pat.sub(' ', expr)
        if new_expr == expr:
            break
        expr = re.sub(r'\s+', ' ', new_expr).strip()

    # Unwrap common constant macros
    for macro in (
        "G_GUINT64_CONSTANT", "G_GUINT32_CONSTANT", "G_GUINT16_CONSTANT",
        "G_GINT64_CONSTANT", "G_GINT32_CONSTANT", "G_GINT16_CONSTANT",
        "GUINT16_TO_BE", "GUINT16_FROM_BE", "GUINT32_TO_BE", "GUINT32_FROM_BE",
        "g_htons", "htons", "g_ntohs", "ntohs",
    ):
        expr = re.sub(r'\b' + re.escape(macro) + r'\s*\(\s*([^)]+?)\s*\)', r'(\1)', expr)

    return expr.strip()


class _SafeIntEvaluator:
    def __init__(self, define_map: Dict[str, str], enum_map: Dict[str, int]):
        self.define_map = define_map
        self.enum_map = enum_map
        self._cache: Dict[str, Optional[int]] = {}

    def resolve_ident(self, name: str, stack: Optional[set] = None) -> Optional[int]:
        if name in self._cache:
            return self._cache[name]
        if stack is None:
            stack = set()
        if name in stack:
            self._cache[name] = None
            return None
        stack.add(name)

        if name in self.enum_map:
            val = self.enum_map[name]
            self._cache[name] = val
            return val

        if name in ("TRUE", "true"):
            self._cache[name] = 1
            return 1
        if name in ("FALSE", "false"):
            self._cache[name] = 0
            return 0
        if name in ("NULL",):
            self._cache[name] = 0
            return 0

        expr = self.define_map.get(name)
        if expr is None:
            self._cache[name] = None
            return None

        val = self.eval_expr(expr, stack=stack)
        self._cache[name] = val
        return val

    def eval_expr(self, expr: str, stack: Optional[set] = None) -> Optional[int]:
        if stack is None:
            stack = set()
        expr = _normalize_c_expr(expr)
        if not expr:
            return None

        # Replace identifiers
        def repl(m: re.Match) -> str:
            ident = m.group(0)
            if ident in ("and", "or", "not"):
                return ident
            v = self.resolve_ident(ident, stack=stack)
            if v is None:
                return ident
            return str(v)

        expr2 = re.sub(r'\b[A-Za-z_]\w*\b', repl, expr)

        # If unresolved identifiers remain, attempt to handle a few known ones by ignoring them as 0
        # (only if expression otherwise looks numeric / simple).
        if re.search(r'\b[A-Za-z_]\w*\b', expr2):
            def repl2(m: re.Match) -> str:
                ident = m.group(0)
                if ident in ("and", "or", "not"):
                    return ident
                v = self.resolve_ident(ident, stack=stack)
                if v is None:
                    return "0"
                return str(v)
            expr2 = re.sub(r'\b[A-Za-z_]\w*\b', repl2, expr2)

        expr2 = expr2.replace("||", " or ").replace("&&", " and ").replace("!", " not ")
        expr2 = re.sub(r'\s+', ' ', expr2).strip()

        # Validate allowed characters/tokens for AST parsing
        try:
            node = ast.parse(expr2, mode='eval')
        except Exception:
            return None

        allowed_nodes = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
            ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div, ast.Mod,
            ast.BitOr, ast.BitAnd, ast.BitXor, ast.Invert,
            ast.LShift, ast.RShift,
            ast.USub, ast.UAdd,
            ast.And, ast.Or, ast.Not,
            ast.BoolOp,
            ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        )

        for n in ast.walk(node):
            if not isinstance(n, allowed_nodes):
                return None

        try:
            val = eval(compile(node, "<c-expr>", "eval"), {"__builtins__": {}}, {})
        except Exception:
            return None

        try:
            if isinstance(val, bool):
                return int(val)
            return int(val)
        except Exception:
            return None


def _parse_gre_80211_proto_expr_from_text(text: str) -> Optional[str]:
    if "gre.proto" not in text:
        return None
    # Capture dissector_add_uint calls
    pat = re.compile(
        r'dissector_add_uint(?:_with_preference)?\s*\(\s*"gre\.proto"\s*,\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)\s*;',
        flags=re.S
    )
    candidates = []
    for m in pat.finditer(text):
        proto_expr = m.group(1).strip()
        handle_expr = m.group(2).strip()
        blob = (proto_expr + " " + handle_expr).lower()
        if any(k in blob for k in ("80211", "802_11", "ieee80211", "wlan", "\"wlan\"", "\"ieee80211\"")):
            candidates.append((proto_expr, handle_expr))
    if not candidates:
        return None
    # Prefer most specific matches
    candidates.sort(key=lambda x: (("80211" not in (x[0] + " " + x[1]).lower()), ("ieee" not in (x[0] + " " + x[1]).lower())))
    return candidates[0][0]


def _find_gre_80211_proto_and_linktype_from_tar(src_path: str) -> Tuple[Optional[str], Optional[int], Dict[str, str], Dict[str, int]]:
    define_map: Dict[str, str] = {}
    enum_map: Dict[str, int] = {}
    proto_expr: Optional[str] = None
    dlt_gre_num: Optional[int] = None
    dlt_gre_expr: Optional[str] = None

    with tarfile.open(src_path, "r:*") as tf:
        members = tf.getmembers()

        def read_text(member) -> Optional[str]:
            if not member.isfile():
                return None
            if member.size <= 0 or member.size > 6_000_000:
                return None
            try:
                f = tf.extractfile(member)
                if f is None:
                    return None
                data = f.read()
            except Exception:
                return None
            try:
                return data.decode("utf-8", "ignore")
            except Exception:
                try:
                    return data.decode("latin-1", "ignore")
                except Exception:
                    return None

        # Prioritize likely relevant files
        prioritized = []
        other = []
        for m in members:
            n = m.name.lower()
            if not m.isfile():
                continue
            if not (n.endswith((".c", ".h"))):
                continue
            base = os.path.basename(n)
            if base == "packet-gre.c" or base == "packet-gre.c.in":
                prioritized.append(m)
            elif "wiretap" in n and ("pcap" in base or "libpcap" in base):
                prioritized.append(m)
            elif ("epan" in n or "wiretap" in n) and base.endswith(".h"):
                other.append(m)
            else:
                other.append(m)

        # First read prioritized and collect proto + dlt quickly
        for m in prioritized:
            text = read_text(m)
            if not text:
                continue
            _collect_defines_and_enums_from_text(text, define_map, enum_map)

            if proto_expr is None:
                pe = _parse_gre_80211_proto_expr_from_text(text)
                if pe:
                    proto_expr = pe

            if dlt_gre_num is None:
                if "WTAP_ENCAP_GRE" in text:
                    m1 = re.search(r'\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*WTAP_ENCAP_GRE\b', text)
                    if m1:
                        try:
                            dlt_gre_num = int(m1.group(1), 0)
                        except Exception:
                            pass
                    if dlt_gre_num is None:
                        m2 = re.search(r'\{\s*([A-Za-z_]\w*)\s*,\s*WTAP_ENCAP_GRE\b', text)
                        if m2:
                            dlt_gre_expr = m2.group(1)
                if dlt_gre_num is None and ("LINKTYPE_GRE" in text or "DLT_GRE" in text):
                    m3 = re.search(r'\b(?:LINKTYPE_GRE|DLT_GRE)\b', text)
                    if m3:
                        # Prefer LINKTYPE_GRE if present
                        if "LINKTYPE_GRE" in text:
                            dlt_gre_expr = "LINKTYPE_GRE"
                        else:
                            dlt_gre_expr = "DLT_GRE"

        # If anything unresolved, scan more headers for defines/enums and possibly proto/dlt
        if proto_expr is None or (dlt_gre_num is None and dlt_gre_expr is None):
            for m in other:
                text = read_text(m)
                if not text:
                    continue
                _collect_defines_and_enums_from_text(text, define_map, enum_map)
                if proto_expr is None:
                    pe = _parse_gre_80211_proto_expr_from_text(text)
                    if pe:
                        proto_expr = pe
                if dlt_gre_num is None and ("WTAP_ENCAP_GRE" in text):
                    m1 = re.search(r'\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*WTAP_ENCAP_GRE\b', text)
                    if m1:
                        try:
                            dlt_gre_num = int(m1.group(1), 0)
                        except Exception:
                            pass
                    if dlt_gre_num is None:
                        m2 = re.search(r'\{\s*([A-Za-z_]\w*)\s*,\s*WTAP_ENCAP_GRE\b', text)
                        if m2:
                            dlt_gre_expr = m2.group(1)

        # Resolve dlt_gre_expr if needed
        if dlt_gre_num is None and dlt_gre_expr is not None:
            ev = _SafeIntEvaluator(define_map, enum_map)
            dlt_gre_num = ev.eval_expr(dlt_gre_expr)

    return proto_expr, dlt_gre_num, define_map, enum_map


def _iter_files_in_dir(root: str, exts: Tuple[str, ...]) -> Iterable[str]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(exts):
                yield os.path.join(dirpath, fn)


def _find_gre_80211_proto_and_linktype_from_dir(src_dir: str) -> Tuple[Optional[str], Optional[int], Dict[str, str], Dict[str, int]]:
    define_map: Dict[str, str] = {}
    enum_map: Dict[str, int] = {}
    proto_expr: Optional[str] = None
    dlt_gre_num: Optional[int] = None
    dlt_gre_expr: Optional[str] = None

    prioritized_paths = []
    other_paths = []

    for p in _iter_files_in_dir(src_dir, (".c", ".h")):
        n = p.replace("\\", "/").lower()
        base = os.path.basename(n)
        if base == "packet-gre.c" or base == "packet-gre.c.in":
            prioritized_paths.append(p)
        elif "/wiretap/" in n and ("pcap" in base or "libpcap" in base):
            prioritized_paths.append(p)
        elif ("/epan/" in n or "/wiretap/" in n) and base.endswith(".h"):
            other_paths.append(p)
        else:
            other_paths.append(p)

    def read_text(path: str) -> Optional[str]:
        try:
            if os.path.getsize(path) > 6_000_000:
                return None
            with open(path, "rb") as f:
                data = f.read()
            return data.decode("utf-8", "ignore")
        except Exception:
            return None

    for p in prioritized_paths:
        text = read_text(p)
        if not text:
            continue
        _collect_defines_and_enums_from_text(text, define_map, enum_map)
        if proto_expr is None:
            pe = _parse_gre_80211_proto_expr_from_text(text)
            if pe:
                proto_expr = pe
        if dlt_gre_num is None:
            if "WTAP_ENCAP_GRE" in text:
                m1 = re.search(r'\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*WTAP_ENCAP_GRE\b', text)
                if m1:
                    try:
                        dlt_gre_num = int(m1.group(1), 0)
                    except Exception:
                        pass
                if dlt_gre_num is None:
                    m2 = re.search(r'\{\s*([A-Za-z_]\w*)\s*,\s*WTAP_ENCAP_GRE\b', text)
                    if m2:
                        dlt_gre_expr = m2.group(1)
            if dlt_gre_num is None and ("LINKTYPE_GRE" in text or "DLT_GRE" in text):
                if "LINKTYPE_GRE" in text:
                    dlt_gre_expr = "LINKTYPE_GRE"
                else:
                    dlt_gre_expr = "DLT_GRE"

    if proto_expr is None or (dlt_gre_num is None and dlt_gre_expr is None):
        for p in other_paths:
            text = read_text(p)
            if not text:
                continue
            _collect_defines_and_enums_from_text(text, define_map, enum_map)
            if proto_expr is None:
                pe = _parse_gre_80211_proto_expr_from_text(text)
                if pe:
                    proto_expr = pe
            if dlt_gre_num is None and "WTAP_ENCAP_GRE" in text:
                m1 = re.search(r'\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*WTAP_ENCAP_GRE\b', text)
                if m1:
                    try:
                        dlt_gre_num = int(m1.group(1), 0)
                    except Exception:
                        pass
                if dlt_gre_num is None:
                    m2 = re.search(r'\{\s*([A-Za-z_]\w*)\s*,\s*WTAP_ENCAP_GRE\b', text)
                    if m2:
                        dlt_gre_expr = m2.group(1)

    if dlt_gre_num is None and dlt_gre_expr is not None:
        ev = _SafeIntEvaluator(define_map, enum_map)
        dlt_gre_num = ev.eval_expr(dlt_gre_expr)

    return proto_expr, dlt_gre_num, define_map, enum_map


def _internet_checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + data[i + 1]
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _build_pcap(dlt: int, pkt: bytes) -> bytes:
    ghdr = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, dlt & 0xFFFFFFFF)
    phdr = struct.pack("<IIII", 0, 0, len(pkt), len(pkt))
    return ghdr + phdr + pkt


def _build_gre_packet(proto: int, payload: bytes = b"\x00") -> bytes:
    flags_ver = 0x0000
    return struct.pack(">HH", flags_ver, proto & 0xFFFF) + payload


def _build_ipv4_gre_packet(gre_proto: int, gre_payload: bytes = b"\x00") -> bytes:
    gre = _build_gre_packet(gre_proto, gre_payload)
    ver_ihl = (4 << 4) | 5
    tos = 0
    total_len = 20 + len(gre)
    ident = 0
    flags_frag = 0
    ttl = 64
    proto = 47  # GRE
    checksum = 0
    src = b"\x00\x00\x00\x00"
    dst = b"\x00\x00\x00\x00"
    iphdr = struct.pack(">BBHHHBBH4s4s", ver_ihl, tos, total_len, ident, flags_frag, ttl, proto, checksum, src, dst)
    csum = _internet_checksum(iphdr)
    iphdr = struct.pack(">BBHHHBBH4s4s", ver_ihl, tos, total_len, ident, flags_frag, ttl, proto, csum, src, dst)
    return iphdr + gre


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            proto_expr, dlt_gre, define_map, enum_map = _find_gre_80211_proto_and_linktype_from_dir(src_path)
        else:
            proto_expr, dlt_gre, define_map, enum_map = _find_gre_80211_proto_and_linktype_from_tar(src_path)

        ev = _SafeIntEvaluator(define_map, enum_map)

        gre_proto_val: Optional[int] = None
        if proto_expr:
            gre_proto_val = ev.eval_expr(proto_expr)

        if gre_proto_val is None:
            # Very conservative fallback: known GRE protocol types won't reliably hit 802.11,
            # but attempt one common constant if present.
            for fallback_name in ("ETHERTYPE_IEEE802_11", "ETHERTYPE_IEEE_802_11", "GRE_PROTO_IEEE80211", "GRE_PROTO_IEEE_802_11"):
                gre_proto_val = ev.resolve_ident(fallback_name)
                if gre_proto_val is not None:
                    break

        if gre_proto_val is None:
            # Last resort: craft something that still parses as GRE but may not dispatch.
            gre_proto_val = 0x0000

        gre_proto_val &= 0xFFFF

        # Prefer direct GRE encapsulation if linktype is found; else fallback to RAW IP.
        if dlt_gre is not None and 0 <= dlt_gre <= 0xFFFFFFFF:
            pkt = _build_gre_packet(gre_proto_val, b"\x00")
            return _build_pcap(int(dlt_gre), pkt)

        # Fallback: DLT_RAW (12) with IPv4+GRE
        pkt = _build_ipv4_gre_packet(gre_proto_val, b"\x00")
        return _build_pcap(12, pkt)