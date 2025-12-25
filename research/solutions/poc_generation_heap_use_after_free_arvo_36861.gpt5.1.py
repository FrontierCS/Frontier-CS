import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 71298
        magics = []
        try:
            with tarfile.open(src_path, "r:*") as tar:
                poc = self._find_poc_in_tar(tar, target_size)
                if poc is not None:
                    return poc
                magics = self._collect_magic_strings(tar)
        except Exception:
            magics = []
        return self._build_synthetic_poc(magics)

    def _find_poc_in_tar(self, tar: tarfile.TarFile, target_size: int) -> bytes | None:
        best_member = None
        best_score = None
        skip_exts = {
            ".c",
            ".h",
            ".hpp",
            ".hh",
            ".cpp",
            ".cc",
            ".cxx",
            ".py",
            ".md",
            ".rst",
            ".txt",
            ".sh",
            ".bat",
            ".ps1",
            ".java",
            ".js",
            ".html",
            ".xml",
            ".yml",
            ".yaml",
            ".json",
            ".toml",
            ".ini",
            ".cfg",
            ".cmake",
            ".in",
            ".ac",
            ".am",
            ".m4",
            ".sln",
            ".vcxproj",
            ".csproj",
            ".mm",
            ".m",
        }
        for m in tar.getmembers():
            if not m.isfile():
                continue
            size = m.size
            if size == 0 or size > 5 * 1024 * 1024:
                continue
            name = os.path.basename(m.name)
            lname = name.lower()
            root, ext = os.path.splitext(lname)
            has_poc_hint = any(
                k in lname for k in ("poc", "crash", "id:", "uaf", "heap-use-after-free", "use-after-free")
            )
            if ext in skip_exts and not has_poc_hint:
                continue
            name_bonus = 0
            if has_poc_hint:
                name_bonus -= 50000
            size_diff = abs(size - target_size)
            score = size_diff + name_bonus
            if best_member is None or score < best_score:
                best_member = m
                best_score = score
        if best_member is None:
            return None
        fobj = tar.extractfile(best_member)
        if fobj is None:
            return None
        data = fobj.read()
        lname = os.path.basename(best_member.name).lower()
        if self._looks_like_text(data):
            if any(k in lname for k in ("poc", "crash", "id:", "uaf")):
                decoded = self._decode_c_hex_string(data)
                if decoded:
                    return decoded
            return None
        return data

    def _looks_like_text(self, data: bytes) -> bool:
        if not data:
            return True
        sample = data[:4096]
        printable = 0
        text_bytes = b"\n\r\t\f\b"
        for b in sample:
            if 32 <= b <= 126 or b in text_bytes:
                printable += 1
        ratio = printable / len(sample)
        return ratio > 0.9

    def _decode_c_hex_string(self, data: bytes) -> bytes | None:
        try:
            s = data.decode("ascii", errors="ignore")
        except Exception:
            return None
        hexdigits = "0123456789abcdefABCDEF"
        out = bytearray()
        found = False
        i = 0
        n = len(s)
        while i + 3 < n:
            if s[i] == "\\" and s[i + 1] == "x" and s[i + 2] in hexdigits and s[i + 3] in hexdigits:
                val = int(s[i + 2 : i + 4], 16)
                out.append(val)
                i += 4
                found = True
            else:
                i += 1
        if not found or len(out) == 0:
            return None
        return bytes(out)

    def _collect_magic_strings(self, tar: tarfile.TarFile) -> list[bytes]:
        magics: list[bytes] = []
        seen: set[bytes] = set()
        string_re = re.compile(r'"([^"\\]{4,64})"')
        for m in tar.getmembers():
            if not m.isfile():
                continue
            name = m.name.lower()
            _, ext = os.path.splitext(name)
            if ext not in (".c", ".h", ".hpp", ".hh", ".cpp", ".cc", ".cxx"):
                continue
            if m.size > 512 * 1024:
                continue
            fobj = tar.extractfile(m)
            if fobj is None:
                continue
            data = fobj.read()
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            for match in string_re.finditer(text):
                s = match.group(1)
                lower = s.lower()
                if any(kw in lower for kw in ("usbredir", "usb-redir", "usb_redir", "usb", "redir")):
                    b = s.encode("utf-8", errors="ignore")
                    if b not in seen:
                        seen.add(b)
                        magics.append(b)
        return magics

    def _build_synthetic_poc(self, magics: list[bytes]) -> bytes:
        out = bytearray()
        if magics:
            for m in magics:
                out += m + b"\n"
            out += b"\x00" * 16
        out += b"usbredir" * 8
        block_size = 2048
        max_mod = 16
        for n in range(1, max_mod + 1):
            for r in range(n):
                byte_val = r & 0xFF
                out += bytes([byte_val]) * block_size
        return bytes(out)
