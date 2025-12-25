import os
import re
import tarfile
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


class _FileProvider:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self._is_dir = os.path.isdir(src_path)
        self._tar = None
        self._members = None  # type: Optional[List[tarfile.TarInfo]]

        if not self._is_dir:
            self._tar = tarfile.open(src_path, mode="r:*")
            self._members = [m for m in self._tar.getmembers() if m.isfile()]

    def close(self):
        if self._tar is not None:
            try:
                self._tar.close()
            except Exception:
                pass
            self._tar = None
        self._members = None

    def iter_paths(self) -> Iterator[str]:
        if self._is_dir:
            for root, _, files in os.walk(self.src_path):
                for fn in files:
                    yield os.path.join(root, fn)
        else:
            assert self._members is not None
            for m in self._members:
                yield m.name

    def read_text(self, path: str, max_bytes: int = 2_000_000) -> Optional[str]:
        try:
            if self._is_dir:
                if os.path.getsize(path) > max_bytes:
                    return None
                with open(path, "rb") as f:
                    data = f.read(max_bytes + 1)
            else:
                assert self._tar is not None
                assert self._members is not None
                m = self._tar.getmember(path)
                if m.size > max_bytes:
                    return None
                f = self._tar.extractfile(m)
                if f is None:
                    return None
                data = f.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return None

    def read_text_by_suffix_pred(self, suffixes: Tuple[str, ...], pred) -> Iterator[Tuple[str, str]]:
        for p in self.iter_paths():
            bn = os.path.basename(p)
            if bn.endswith(suffixes) or p.endswith(suffixes):
                txt = self.read_text(p)
                if not txt:
                    continue
                if pred(p, txt):
                    yield p, txt

    def iter_small_sources(self, max_bytes: int = 2_000_000) -> Iterator[Tuple[str, str]]:
        def pred(_p, _t):
            return True

        for p in self.iter_paths():
            if not (p.endswith(".c") or p.endswith(".h") or p.endswith(".cc") or p.endswith(".cpp")):
                continue
            txt = self.read_text(p, max_bytes=max_bytes)
            if not txt:
                continue
            yield p, txt


class _MacroResolver:
    _define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$')

    def __init__(self, provider: _FileProvider):
        self.provider = provider
        self._def_cache: Dict[str, Optional[str]] = {}
        self._val_cache: Dict[str, Optional[int]] = {}

    @staticmethod
    def _strip_comments(s: str) -> str:
        s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
        s = re.sub(r"//.*", " ", s)
        return s.strip()

    @staticmethod
    def _strip_numeric_suffixes(expr: str) -> str:
        def repl(m):
            return m.group(1)
        return re.sub(r"(\b0x[0-9A-Fa-f]+|\b\d+)\s*[uUlL]+\b", repl, expr)

    @staticmethod
    def _remove_simple_casts(expr: str) -> str:
        # Remove C-style casts like (guint16), (unsigned int), etc.
        # Keep parentheses that likely represent grouping with operators or numbers.
        return re.sub(r"\(\s*[A-Za-z_][A-Za-z0-9_\s\*]*\s*\)", "", expr)

    @staticmethod
    def _unwrap_simple_macros(expr: str) -> str:
        # Convert wrappers like UINT16_C(0x1234) -> (0x1234)
        # Repeat until stable.
        prev = None
        cur = expr
        for _ in range(8):
            if cur == prev:
                break
            prev = cur
            cur = re.sub(r"\b([A-Za-z_]\w*)\s*\(\s*([^\(\)]+?)\s*\)", r"(\2)", cur)
        return cur

    def find_define_expr(self, name: str) -> Optional[str]:
        if name in self._def_cache:
            return self._def_cache[name]
        target = name

        def is_candidate_path(p: str) -> bool:
            bn = os.path.basename(p).lower()
            if bn in ("etypes.h", "etypes.h.in", "ethertype.h", "packet-gre.c", "packet-ieee80211.c"):
                return True
            if "etype" in bn or "ethertype" in bn or "gre" in bn or "80211" in bn or "wlan" in bn:
                return True
            if "/epan/" in p or "/wiretap/" in p or "\\epan\\" in p or "\\wiretap\\" in p:
                return True
            return False

        # Prefer likely headers/sources first
        prioritized: List[Tuple[str, str]] = []
        others: List[Tuple[str, str]] = []
        for p, txt in self.provider.iter_small_sources(max_bytes=1_500_000):
            if is_candidate_path(p):
                prioritized.append((p, txt))
            else:
                others.append((p, txt))

        for _, txt in prioritized + others:
            for line in txt.splitlines():
                m = self._define_re.match(line)
                if not m:
                    continue
                if m.group(1) != target:
                    continue
                rhs = m.group(2).rstrip()
                rhs = self._strip_comments(rhs)
                # Handle multi-line continuation
                if rhs.endswith("\\"):
                    accum = rhs[:-1].rstrip()
                    # find subsequent lines is expensive without context; but most constants are single-line
                    rhs = accum
                self._def_cache[name] = rhs
                return rhs

        self._def_cache[name] = None
        return None

    def eval_macro(self, name: str, _depth: int = 0) -> Optional[int]:
        if name in self._val_cache:
            return self._val_cache[name]
        if _depth > 32:
            self._val_cache[name] = None
            return None
        expr = self.find_define_expr(name)
        if expr is None:
            self._val_cache[name] = None
            return None
        val = self.eval_expr(expr, _depth=_depth + 1)
        self._val_cache[name] = val
        return val

    def eval_expr(self, expr: str, _depth: int = 0) -> Optional[int]:
        if _depth > 64:
            return None
        e = self._strip_comments(expr)
        e = self._strip_numeric_suffixes(e)
        e = self._remove_simple_casts(e)
        e = self._unwrap_simple_macros(e)
        e = e.strip()

        # Fast numeric parse
        m = re.fullmatch(r"\(?\s*(0x[0-9A-Fa-f]+|\d+)\s*\)?", e)
        if m:
            try:
                return int(m.group(1), 0)
            except Exception:
                return None

        # Replace known macro names in expression progressively
        # We'll parse names and resolve them.
        name_re = re.compile(r"\b([A-Za-z_]\w*)\b")
        names = set(name_re.findall(e))
        # Remove common keywords
        keywords = {
            "sizeof", "struct", "unsigned", "signed", "int", "short", "long", "char",
            "void", "const", "volatile", "enum", "static", "extern", "register", "auto",
            "inline", "restrict"
        }
        names = {n for n in names if n not in keywords}

        # Iteratively substitute resolvable names
        subs: Dict[str, int] = {}
        for n in sorted(names, key=len, reverse=True):
            v = self.eval_macro(n, _depth=_depth + 1)
            if v is not None:
                subs[n] = v

        if subs:
            # Replace word-boundary occurrences
            def sub_fn(mo):
                nm = mo.group(1)
                if nm in subs:
                    return str(subs[nm])
                return nm
            e2 = name_re.sub(sub_fn, e)
        else:
            e2 = e

        # Keep only safe characters/operators
        if re.search(r"[^0-9A-Fa-fxX\(\)\s\+\-\*\&\|\^\~\<\>\/%]", e2):
            return None

        # Parse and evaluate AST safely
        try:
            import ast

            node = ast.parse(e2, mode="eval")

            def eval_node(n) -> int:
                if isinstance(n, ast.Expression):
                    return eval_node(n.body)
                if isinstance(n, ast.Constant) and isinstance(n.value, int):
                    return int(n.value)
                if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert)):
                    v = eval_node(n.operand)
                    if isinstance(n.op, ast.UAdd):
                        return +v
                    if isinstance(n.op, ast.USub):
                        return -v
                    return ~v
                if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
                                                                 ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor)):
                    a = eval_node(n.left)
                    b = eval_node(n.right)
                    op = n.op
                    if isinstance(op, ast.Add):
                        return a + b
                    if isinstance(op, ast.Sub):
                        return a - b
                    if isinstance(op, ast.Mult):
                        return a * b
                    if isinstance(op, ast.FloorDiv):
                        if b == 0:
                            return 0
                        return a // b
                    if isinstance(op, ast.Mod):
                        if b == 0:
                            return 0
                        return a % b
                    if isinstance(op, ast.LShift):
                        return a << b
                    if isinstance(op, ast.RShift):
                        return a >> b
                    if isinstance(op, ast.BitOr):
                        return a | b
                    if isinstance(op, ast.BitAnd):
                        return a & b
                    if isinstance(op, ast.BitXor):
                        return a ^ b
                raise ValueError("unsupported expression")

            return int(eval_node(node))
        except Exception:
            return None


def _extract_gre_80211_proto_token(provider: _FileProvider) -> Optional[str]:
    gre_sources: List[Tuple[str, str]] = []
    for p, txt in provider.iter_small_sources(max_bytes=2_000_000):
        bn = os.path.basename(p).lower()
        if "gre" in bn and (bn.endswith(".c") or bn.endswith(".cc") or bn.endswith(".cpp")):
            if '"gre.proto"' in txt and "dissector_add_uint" in txt:
                gre_sources.append((p, txt))
            elif "gre.proto" in txt and "dissector_add_uint" in txt:
                gre_sources.append((p, txt))
        elif bn == "packet-gre.c":
            gre_sources.append((p, txt))

    # Prioritize packet-gre.c
    gre_sources.sort(key=lambda x: (0 if os.path.basename(x[0]).lower() == "packet-gre.c" else 1, len(x[1])))

    add_re = re.compile(
        r'dissector_add_uint(?:_with_preference)?\s*\(\s*"gre\.proto"\s*,\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)\s*;',
        re.MULTILINE,
    )

    best_token = None
    for _, txt in gre_sources:
        for m in add_re.finditer(txt):
            key = m.group(1).strip()
            handle = m.group(2).strip()
            line = m.group(0)
            key_l = key.lower()
            handle_l = handle.lower()
            line_l = line.lower()
            if ("80211" in handle_l) or ("802_11" in handle_l) or ("ieee80211" in handle_l) or ("wlan" in handle_l):
                best_token = key
                break
            if ("80211" in key_l) or ("802_11" in key_l) or ("ieee80211" in key_l):
                best_token = key
                break
            if ("802.11" in line_l) or ("ieee 802.11" in line_l):
                best_token = key
                break
        if best_token is not None:
            break

    if best_token is None:
        # fallback: look for any mention of ieee80211 in gre source and grab the closest dissector_add_uint line
        for _, txt in gre_sources:
            if "ieee80211" not in txt.lower() and "80211" not in txt.lower():
                continue
            for m in add_re.finditer(txt):
                key = m.group(1).strip()
                handle = m.group(2).strip()
                if "gre.proto" in m.group(0) and ("proto" in key.lower() or "ether" in key.lower() or "0x" in key.lower() or key.strip().isdigit()):
                    if "ieee" in handle.lower() or "wlan" in handle.lower() or "802" in handle.lower():
                        best_token = key
                        break
            if best_token is not None:
                break

    if best_token is not None:
        best_token = re.sub(r"/\*.*?\*/", " ", best_token, flags=re.S).strip()
        best_token = re.sub(r"//.*", " ", best_token).strip()
        return best_token

    return None


def _parse_token_to_int(token: str, resolver: _MacroResolver) -> Optional[int]:
    t = token.strip()
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//.*", " ", t)
    t = t.strip()
    # remove casts at beginning: (guint16)FOO
    t = re.sub(r"^\(\s*[A-Za-z_][A-Za-z0-9_\s\*]*\s*\)\s*", "", t).strip()
    # try resolve as expr
    v = resolver.eval_expr(t)
    if v is not None:
        return v & 0xFFFF
    # If it's a macro name
    if re.fullmatch(r"[A-Za-z_]\w*", t):
        v2 = resolver.eval_macro(t)
        if v2 is not None:
            return v2 & 0xFFFF
    return None


def _build_80211_beacon_payload() -> bytes:
    fc = b"\x80\x00"
    dur = b"\x00\x00"
    addr1 = b"\xff\xff\xff\xff\xff\xff"
    addr2 = b"\x00\x11\x22\x33\x44\x55"
    addr3 = b"\x00\x11\x22\x33\x44\x55"
    seq = b"\x10\x00"
    timestamp = b"\x00" * 8
    interval = b"\x64\x00"
    cap = b"\x01\x04"
    ssid = b"\x00\x00"          # SSID tag: id=0, len=0
    rates = b"\x01\x01\x82"     # Supported Rates: id=1, len=1, rate=0x82
    payload = fc + dur + addr1 + addr2 + addr3 + seq + timestamp + interval + cap + ssid + rates
    return payload


class Solution:
    def solve(self, src_path: str) -> bytes:
        provider = _FileProvider(src_path)
        try:
            token = _extract_gre_80211_proto_token(provider)
            resolver = _MacroResolver(provider)
            proto = None
            if token:
                proto = _parse_token_to_int(token, resolver)

            if proto is None:
                # Heuristic fallbacks (rarely needed)
                for cand in (0x0016, 0x0017, 0x6558, 0x88BE, 0x88BF):
                    proto = cand
                    break

            flags_version = 0x0000
            gre_hdr = flags_version.to_bytes(2, "big") + (proto & 0xFFFF).to_bytes(2, "big")
            payload = _build_80211_beacon_payload()
            return gre_hdr + payload
        finally:
            provider.close()