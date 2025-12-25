import os
import re
import io
import tarfile
import tempfile
import struct
from typing import Dict, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._prepare_source_tree(src_path)
        proto = self._find_ieee80211_gre_proto(root)
        if proto is None:
            proto = 0x0019
        return self._build_pcap_gre(proto)

    def _prepare_source_tree(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="src_")
        with tarfile.open(src_path, "r:*") as tf:
            self._safe_extract(tf, tmpdir)
        return tmpdir

    def _safe_extract(self, tf: tarfile.TarFile, dest: str) -> None:
        dest_abs = os.path.abspath(dest) + os.sep
        members = []
        for m in tf.getmembers():
            name = m.name
            if not name or name == ".":
                continue
            name = name.replace("\\", "/")
            if name.startswith("/") or name.startswith("../") or "/../" in name:
                continue
            out_path = os.path.abspath(os.path.join(dest, name))
            if not out_path.startswith(dest_abs):
                continue
            members.append(m)
        tf.extractall(dest, members=members)

    def _build_pcap_gre(self, gre_proto: int) -> bytes:
        # Classic pcap, little-endian, LINKTYPE_GRE (47)
        global_hdr = struct.pack(
            "<IHHIIII",
            0xA1B2C3D4,  # magic (written LE => d4 c3 b2 a1)
            2, 4,        # version
            0,           # thiszone
            0,           # sigfigs
            0xFFFF,      # snaplen
            47           # network (LINKTYPE_GRE / DLT_GRE)
        )

        gre_pkt = struct.pack("!HHB", 0x0000, gre_proto & 0xFFFF, 0x00)  # 5 bytes total
        rec_hdr = struct.pack("<IIII", 0, 0, len(gre_pkt), len(gre_pkt))
        return global_hdr + rec_hdr + gre_pkt

    def _find_ieee80211_gre_proto(self, root: str) -> Optional[int]:
        # Build numeric defines map from headers for resolving macro keys
        defines = self._collect_defines(root)

        candidates = []
        # Prefer searching for gre.proto usage; it should be relatively sparse
        for path in self._iter_source_files(root):
            try:
                sz = os.path.getsize(path)
                if sz <= 0 or sz > 8 * 1024 * 1024:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue

            if b"gre.proto" not in data:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue

            # Capture dissector_add_uint("gre.proto", KEY, HANDLE);
            for m in re.finditer(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)\s*;', text):
                key_expr = m.group(1).strip()
                handle_expr = m.group(2)
                hlow = handle_expr.lower()
                if ("ieee80211" in hlow) or ("802_11" in hlow) or ("802.11" in hlow) or ("wlan" in hlow):
                    key_val = self._resolve_c_int_expr(key_expr, defines)
                    if key_val is not None:
                        candidates.append(key_val & 0xFFFF)

            # Also check dissector_add_uint("gre.proto", KEY, find_dissector("wlan"));
            for m in re.finditer(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([^,]+?)\s*,\s*find_dissector\s*\(\s*"([^"]+)"\s*\)\s*\)\s*;', text):
                key_expr = m.group(1).strip()
                dissector_name = m.group(2).lower()
                if ("ieee80211" in dissector_name) or ("802_11" in dissector_name) or ("802.11" in dissector_name) or ("wlan" in dissector_name):
                    key_val = self._resolve_c_int_expr(key_expr, defines)
                    if key_val is not None:
                        candidates.append(key_val & 0xFFFF)

        if candidates:
            # Prefer 0x0019 if present, else first
            if 0x0019 in candidates:
                return 0x0019
            return candidates[0]

        # Fallback heuristic: look for a define that suggests IEEE80211 ethertype
        for k, v in defines.items():
            kn = k.lower()
            if ("ethertype" in kn or "ether_type" in kn) and ("802_11" in kn or "802.11" in kn or "ieee80211" in kn or "wlan" in kn):
                return v & 0xFFFF

        return None

    def _iter_source_files(self, root: str):
        exts = (".c", ".h", ".cc", ".cpp", ".hh", ".hpp", ".inc", ".inl")
        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath).lower()
            if dn in (".git", ".svn", "build", "out", "cmake-build-debug", "cmake-build-release"):
                dirnames[:] = []
                continue
            for fn in filenames:
                fl = fn.lower()
                if fl.endswith(exts):
                    yield os.path.join(dirpath, fn)

    def _collect_defines(self, root: str) -> Dict[str, int]:
        defines: Dict[str, int] = {}
        define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/[*].*?[*]/\s*)?(?://.*)?$')
        for path in self._iter_source_files(root):
            if not path.lower().endswith(".h"):
                continue
            try:
                sz = os.path.getsize(path)
                if sz <= 0 or sz > 3 * 1024 * 1024:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
                text = data.decode("utf-8", "ignore")
            except OSError:
                continue
            except Exception:
                continue

            for line in text.splitlines():
                m = define_re.match(line)
                if not m:
                    continue
                name = m.group(1)
                rhs = m.group(2).strip()
                if not rhs:
                    continue
                # Only store simple numeric defines
                val = self._parse_c_int_literal(rhs)
                if val is None:
                    # Handle parentheses around a literal: (0x1234)
                    rhs2 = rhs
                    for _ in range(2):
                        rhs2 = rhs2.strip()
                        if rhs2.startswith("(") and rhs2.endswith(")"):
                            rhs2 = rhs2[1:-1].strip()
                        else:
                            break
                    val = self._parse_c_int_literal(rhs2)
                if val is not None:
                    defines.setdefault(name, val)
        return defines

    def _resolve_c_int_expr(self, expr: str, defines: Dict[str, int]) -> Optional[int]:
        expr = expr.strip()
        if not expr:
            return None

        # Remove casts like (guint16) or (unsigned int)
        expr = re.sub(r'^\(\s*[A-Za-z_][\w\s\*]*\)\s*', '', expr).strip()

        # If expression contains operators other than surrounding parentheses, keep it simple:
        # attempt to resolve if it's just IDENT or numeric literal.
        # Remove one layer of parentheses.
        for _ in range(2):
            if expr.startswith("(") and expr.endswith(")"):
                inner = expr[1:-1].strip()
                # avoid stripping if parentheses are part of complex expression
                if inner.count("(") == inner.count(")"):
                    expr = inner
                else:
                    break

        val = self._parse_c_int_literal(expr)
        if val is not None:
            return val

        if re.fullmatch(r'[A-Za-z_]\w*', expr):
            if expr in defines:
                return defines[expr]
            # common alternate: might appear without prefix/suffix
            for k, v in defines.items():
                if k == expr:
                    return v
            return None

        # Try very limited evaluation: IDENT -> value, allow +/- only
        m = re.fullmatch(r'([A-Za-z_]\w*)\s*([+\-])\s*(0x[0-9A-Fa-f]+|\d+)', expr)
        if m:
            base = defines.get(m.group(1))
            if base is None:
                return None
            off = int(m.group(3), 0)
            return base + off if m.group(2) == "+" else base - off

        return None

    def _parse_c_int_literal(self, s: str) -> Optional[int]:
        s = s.strip()
        if not s:
            return None
        # Trim common C suffixes
        s = re.sub(r'(?i)(ull|llu|ul|lu|ll|u|l)\b', '', s).strip()
        # Remove trailing commas or parentheses artifacts
        s = s.rstrip(",")
        # Accept simple numeric only
        if not re.fullmatch(r'0x[0-9A-Fa-f]+|\d+', s):
            return None
        try:
            return int(s, 0)
        except Exception:
            return None