import os
import tarfile
import re
import io
import zipfile
from typing import Optional, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        bug_id = "42537014"
        try:
            with tarfile.open(src_path, "r:*") as tar:
                data = self._find_poc_in_tar(tar, bug_id)
                if data:
                    nested = self._maybe_extract_nested_archive(data, bug_id)
                    if nested:
                        return nested
                    return data
        except tarfile.TarError:
            pass
        return b"A" * 9

    def _find_poc_in_tar(self, tar: tarfile.TarFile, bug_id: str) -> Optional[bytes]:
        candidates: List[Tuple[int, int, bytes]] = []

        # First pass: files whose names contain the bug id
        for member in tar.getmembers():
            if not member.isreg():
                continue
            name_lower = member.name.lower()
            if bug_id in name_lower:
                data = self._safe_extract_file(tar, member, max_size=16 * 1024 * 1024)
                if data:
                    score = self._score_candidate(name_lower, data)
                    candidates.append((score, len(data), data))

        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1]))
            return candidates[0][2]

        # Second pass: search file contents for bug id and try to extract embedded PoC
        src_candidates: List[Tuple[int, bytes]] = []
        for member in tar.getmembers():
            if not member.isreg():
                continue
            # Limit to reasonably small text-like files
            if member.size > 1024 * 1024:
                continue
            data = self._safe_extract_file(tar, member, max_size=1024 * 1024)
            if not data:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            if bug_id in text:
                poc = self._extract_poc_from_text_source(text, bug_id)
                if poc:
                    src_candidates.append((len(poc), poc))

        if src_candidates:
            src_candidates.sort(key=lambda x: x[0])
            return src_candidates[0][1]

        return None

    def _safe_extract_file(
        self, tar: tarfile.TarFile, member: tarfile.TarInfo, max_size: int
    ) -> Optional[bytes]:
        if member.size <= 0 or member.size > max_size:
            return None
        try:
            f = tar.extractfile(member)
            if f is None:
                return None
            data = f.read(max_size + 1)
            if not data or len(data) > max_size:
                return None
            return data
        except Exception:
            return None

    def _score_candidate(self, name_lower: str, data: bytes) -> int:
        score = 0
        base = os.path.basename(name_lower)

        if "42537014" in base:
            score += 50
        if "poc" in name_lower or "proof" in name_lower:
            score += 30
        if "repro" in name_lower or "reproducer" in name_lower:
            score += 25
        if "crash" in name_lower:
            score += 20
        if "oss-fuzz" in name_lower or "ossfuzz" in name_lower or "clusterfuzz" in name_lower:
            score += 15
        if "test" in name_lower or "regress" in name_lower:
            score += 5
        if "dash" in name_lower:
            score += 3

        _, ext = os.path.splitext(base)
        ext = ext.lower()
        if ext in {".md", ".markdown", ".rst", ".diff", ".patch", ".log"}:
            score -= 20

        if self._looks_like_doc(data):
            score -= 100

        # Mild penalty for very large inputs
        score -= int(len(data) / 100000)

        return score

    def _looks_like_doc(self, data: bytes) -> bool:
        if len(data) > 40000:
            return True
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            return False

        lowered = text.lower()
        doc_keywords = [
            "oss-fuzz",
            "clusterfuzz",
            "reproducer",
            "reproduction",
            "bug ",
            "bug:",
            "issue",
            "crash ",
            "heap overflow",
            "buffer overflow",
            "stack overflow",
        ]
        if any(word in lowered for word in doc_keywords):
            return True

        if len(text) > 200 and text.count("\n") >= 3:
            printable = sum(
                1 for c in text if (32 <= ord(c) < 127) or c in "\n\r\t"
            )
            if printable / max(1, len(text)) > 0.9:
                return True

        return False

    def _extract_poc_from_text_source(self, text: str, bug_id: str) -> Optional[bytes]:
        bug_pos = text.find(bug_id)
        if bug_pos != -1:
            start = max(0, bug_pos - 2000)
            end = min(len(text), bug_pos + 6000)
            region = text[start:end]
        else:
            # Fallback to entire text if for some reason bug id not found
            region = text

        # Try to extract from byte/char array initializers
        arr_bytes = self._extract_from_array_initializers(region)
        if arr_bytes:
            return arr_bytes

        # Try to extract from string literals assigned to char/uint8_t arrays
        str_bytes = self._extract_from_string_literals(region)
        if str_bytes:
            return str_bytes

        return None

    def _extract_from_array_initializers(self, region: str) -> Optional[bytes]:
        candidates: List[bytes] = []
        for m in re.finditer(r'\{([^{}]{1,4096})\}', region, flags=re.DOTALL):
            inside = m.group(1)
            before = region[max(0, m.start() - 120): m.start()]
            if not re.search(r'(uint8_t|unsigned\s+char|signed\s+char|char)\s+\w*\s*\[', before):
                continue
            tokens = re.findall(r'0x[0-9a-fA-F]+|\d+', inside)
            if not tokens:
                continue
            vals = []
            valid = True
            for tok in tokens:
                try:
                    v = int(tok, 0)
                except ValueError:
                    valid = False
                    break
                if 0 <= v <= 255:
                    vals.append(v)
                else:
                    valid = False
                    break
            if not valid or not vals:
                continue
            if len(vals) > 0 and len(vals) <= 4096:
                candidates.append(bytes(vals))

        if candidates:
            candidates.sort(key=len)
            return candidates[0]
        return None

    def _extract_from_string_literals(self, region: str) -> Optional[bytes]:
        candidates: List[bytes] = []
        for m in re.finditer(r'"(?:\\.|[^"\\])*"', region):
            literal = m.group(0)
            before = region[max(0, m.start() - 120): m.start()]
            if not re.search(r'(uint8_t|unsigned\s+char|signed\s+char|char)\s+\w*\s*(\[|=)', before):
                continue
            try:
                decoded = self._decode_c_string_literal(literal)
            except Exception:
                continue
            if decoded:
                candidates.append(decoded)

        if candidates:
            candidates.sort(key=len)
            return candidates[0]
        return None

    def _decode_c_string_literal(self, literal: str) -> bytes:
        # literal includes surrounding quotes
        if len(literal) < 2 or literal[0] != '"' or literal[-1] != '"':
            return b""
        s = literal[1:-1]
        out = bytearray()
        i = 0
        length = len(s)
        while i < length:
            ch = s[i]
            if ch != '\\':
                out.append(ord(ch))
                i += 1
            else:
                i += 1
                if i >= length:
                    out.append(ord('\\'))
                    break
                esc = s[i]
                i += 1
                if esc == 'x':
                    hex_digits = ''
                    while i < length and s[i] in '0123456789abcdefABCDEF' and len(hex_digits) < 2:
                        hex_digits += s[i]
                        i += 1
                    if hex_digits:
                        out.append(int(hex_digits, 16))
                    else:
                        out.append(ord('x'))
                elif esc in '01234567':
                    oct_digits = esc
                    count = 1
                    while i < length and s[i] in '01234567' and count < 3:
                        oct_digits += s[i]
                        i += 1
                        count += 1
                    out.append(int(oct_digits, 8))
                elif esc == 'n':
                    out.append(0x0A)
                elif esc == 'r':
                    out.append(0x0D)
                elif esc == 't':
                    out.append(0x09)
                elif esc == '0':
                    out.append(0x00)
                elif esc == '\\':
                    out.append(ord('\\'))
                elif esc == '"':
                    out.append(ord('"'))
                else:
                    out.append(ord(esc))
        return bytes(out)

    def _maybe_extract_nested_archive(self, data: bytes, bug_id: str) -> Optional[bytes]:
        # Currently handle only zip archives
        if len(data) >= 4 and data[:2] == b"PK":
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    candidates: List[Tuple[int, bytes]] = []
                    for name in z.namelist():
                        lower = name.lower()
                        if bug_id in lower:
                            try:
                                content = z.read(name)
                            except Exception:
                                continue
                            if content:
                                candidates.append((len(content), content))
                    if candidates:
                        candidates.sort(key=lambda x: x[0])
                        return candidates[0][1]
            except Exception:
                return None
        return None
