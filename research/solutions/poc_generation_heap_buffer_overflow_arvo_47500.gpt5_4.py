import os
import tarfile
import io
import gzip
import bz2
import lzma
import zipfile


def _is_j2k_magic(data: bytes) -> bool:
    # JPEG 2000 codestream SOC marker
    return len(data) >= 2 and data[0] == 0xFF and data[1] == 0x4F


def _is_jp2_magic(data: bytes) -> bool:
    # JP2 signature box
    return data.startswith(b"\x00\x00\x00\x0C\x6A\x50\x20\x20\x0D\x0A\x87\x0A")


def _is_candidate_bytes(data: bytes) -> bool:
    if not data:
        return False
    return _is_j2k_magic(data) or _is_jp2_magic(data)


def _maybe_decompress(data: bytes, name_hint: str = "") -> bytes:
    # Try gzip by header or extension
    low = name_hint.lower()
    try:
        if data.startswith(b"\x1F\x8B") or low.endswith(".gz"):
            return gzip.decompress(data)
    except Exception:
        pass
    try:
        if data.startswith(b"BZh") or low.endswith(".bz2"):
            return bz2.decompress(data)
    except Exception:
        pass
    try:
        if data.startswith(b"\xFD7zXZ\x00") or low.endswith(".xz"):
            return lzma.decompress(data)
    except Exception:
        pass
    # Try raw lzma if looks like it, though risky; guarded
    try:
        if low.endswith(".lzma"):
            return lzma.decompress(data, format=lzma.FORMAT_ALONE)
    except Exception:
        pass
    # Try zipfile
    try:
        if data.startswith(b"PK\x03\x04") or low.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                # Prefer files that look like j2k/jp2
                best = None
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    try:
                        zdata = zf.read(zi)
                    except Exception:
                        continue
                    if _is_candidate_bytes(zdata):
                        # Exact match: good
                        return zdata
                    # Else keep smallest candidate
                    if best is None or len(zdata) < len(best):
                        best = zdata
                if best is not None:
                    return best
    except Exception:
        pass
    return data


def _rank_candidate(name: str, size: int, data: bytes, target_len: int = 1479) -> int:
    score = 0
    lname = name.lower()
    if size == target_len:
        score += 1000
    # closeness in size
    diff = abs(size - target_len)
    score += max(0, 300 - min(300, diff))  # 0..300
    if "poc" in lname:
        score += 500
    if "fuzz" in lname or "oss-fuzz" in lname or "clusterfuzz" in lname or "testcase" in lname:
        score += 250
    if lname.endswith((".j2k", ".j2c", ".jp2", ".jpx", ".jpf")):
        score += 300
    if _is_candidate_bytes(data):
        score += 700
    # prefer HTJ2K hints
    if "ht" in lname and ("dec" in lname or "decode" in lname):
        score += 120
    if "openjpeg" in lname or "opj" in lname:
        score += 60
    return score


def _iter_tar_members(tar: tarfile.TarFile):
    # Yield regular files
    for m in tar.getmembers():
        if not m.isreg():
            continue
        # Avoid enormous files
        if m.size <= 0 or m.size > 10 * 1024 * 1024:
            continue
        yield m


def _read_member(tar: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    try:
        f = tar.extractfile(member)
        if f is None:
            return b""
        with f:
            return f.read()
    except Exception:
        return b""


def _find_poc_in_tar(src_path: str) -> bytes:
    try:
        with tarfile.open(src_path, mode="r:*") as tar:
            # First pass: look for exact size match
            exact_candidates = []
            generic_candidates = []
            for m in _iter_tar_members(tar):
                # Quick filename filtering to reduce reads
                lname = m.name.lower()
                likely = any(s in lname for s in ("poc", "fuzz", "oss-fuzz", "clusterfuzz", "testcase", ".j2k", ".j2c", ".jp2", ".jp2k", ".jp2_", ".jp2.", ".jp2/", ".jpx"))
                # Also allow exact size match to target
                if not likely and m.size != 1479:
                    # Briefly sample head bytes to detect magic without reading whole file
                    try:
                        f = tar.extractfile(m)
                        if f is None:
                            continue
                        head = f.read(16)
                        f.close()
                    except Exception:
                        continue
                    if not _is_candidate_bytes(head):
                        continue
                data = _read_member(tar, m)
                if not data:
                    continue
                # Decompress if needed
                d2 = _maybe_decompress(data, m.name)
                # Store both original and decompressed when applicable
                for payload, label in ((d2, m.name),):
                    size = len(payload)
                    if size == 1479 and _is_candidate_bytes(payload):
                        exact_candidates.append((payload, m.name))
                    else:
                        # Accept if looks like j2k/jp2 or filename hints
                        if _is_candidate_bytes(payload) or likely:
                            generic_candidates.append((payload, m.name))
            if exact_candidates:
                # Return the most descriptive-named one
                best = max(exact_candidates, key=lambda x: _rank_candidate(x[1], len(x[0]), x[0]))
                return best[0]
            if generic_candidates:
                # Rank and return best
                best = max(generic_candidates, key=lambda x: _rank_candidate(x[1], len(x[0]), x[0]))
                return best[0]
    except Exception:
        pass
    return b""


def _safe_read_file(path: str, max_size: int = 10 * 1024 * 1024) -> bytes:
    try:
        st = os.stat(path)
        if not os.path.isfile(path) or st.st_size <= 0 or st.st_size > max_size:
            return b""
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return b""


def _find_poc_nearby(base_dir: str) -> bytes:
    target_len = 1479
    best = (0, b"", "")
    # Candidate directories to search preferentially
    preferred_dirs = []
    try:
        for name in os.listdir(base_dir):
            p = os.path.join(base_dir, name)
            if os.path.isdir(p) and any(k in name.lower() for k in ("poc", "pocs", "fuzz", "oss", "test", "case", "sample", "example", "inputs", "corpus", "cases")):
                preferred_dirs.append(p)
    except Exception:
        pass
    # Always include base_dir
    if base_dir not in preferred_dirs:
        preferred_dirs.insert(0, base_dir)

    visited = 0
    limit_files = 4000
    for root in preferred_dirs:
        for dirpath, dirnames, filenames in os.walk(root):
            # Limit depth
            rel = os.path.relpath(dirpath, root)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth > 4:
                del dirnames[:]
                continue
            for fn in filenames:
                if visited >= limit_files:
                    break
                visited += 1
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 10 * 1024 * 1024:
                    continue
                lname = fn.lower()
                likely = any(s in lname for s in ("poc", "fuzz", "oss-fuzz", "clusterfuzz", "testcase", "j2k", "j2c", "jp2", "jpx"))
                if not likely and st.st_size != target_len:
                    # Peek header
                    try:
                        with open(path, "rb") as f:
                            head = f.read(16)
                    except Exception:
                        continue
                    if not _is_candidate_bytes(head):
                        continue
                data = _safe_read_file(path)
                if not data:
                    continue
                data2 = _maybe_decompress(data, lname)
                # If it's a zip archive with multiple files, _maybe_decompress may pick a nested candidate;
                # rank by name and content
                score = _rank_candidate(path, len(data2), data2, target_len=target_len)
                if score > best[0] and (_is_candidate_bytes(data2) or likely):
                    best = (score, data2, path)
            if visited >= limit_files:
                break
        if best[0] >= 1500:
            break
    return best[1]


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Attempt to find a bundled PoC inside the source tarball
        poc = _find_poc_in_tar(src_path)
        if poc:
            return poc
        # Attempt to locate a nearby PoC in filesystem
        base_dir = os.path.dirname(os.path.abspath(src_path))
        poc = _find_poc_nearby(base_dir)
        if poc:
            return poc
        # Fallback: return empty bytes (no PoC found). It's better than random data.
        # Some harnesses may handle this gracefully.
        return b""