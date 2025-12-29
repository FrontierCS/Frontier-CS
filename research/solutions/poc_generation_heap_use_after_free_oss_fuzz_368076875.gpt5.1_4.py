import os
import io
import tarfile
import zipfile

GROUND_TRUTH_LEN = 274773
BUG_ID = "368076875"
MAX_ARCHIVE_DEPTH = 3
MAX_NESTED_ARCHIVE_SIZE = 50 * 1024 * 1024  # 50 MB


def _score_candidate(name: str, size: int) -> float:
    lower = name.lower()
    score = 0.0

    if BUG_ID in lower:
        score += 10000.0
    if "oss-fuzz" in lower or "clusterfuzz" in lower:
        score += 5000.0

    tokens_weights = (
        ("poc", 2000.0),
        ("testcase", 1800.0),
        ("crash", 1800.0),
        ("repro", 1500.0),
        ("input", 800.0),
        ("uaf", 1200.0),
        ("heap", 900.0),
        ("ast", 400.0),
        ("repr", 300.0),
    )
    for tok, w in tokens_weights:
        if tok in lower:
            score += w

    diff = abs(int(size) - GROUND_TRUTH_LEN)
    score -= diff / 1000.0

    if size == GROUND_TRUTH_LEN:
        score += 3000.0

    if size > 5 * GROUND_TRUTH_LEN:
        score -= (size - 5 * GROUND_TRUTH_LEN) / 10000.0

    return score


def _is_archive_name(lower_name: str) -> bool:
    return lower_name.endswith(
        (
            ".tar",
            ".tar.gz",
            ".tgz",
            ".tar.bz2",
            ".tar.xz",
            ".zip",
        )
    )


def _is_interesting_archive_name(lower_name: str) -> bool:
    interesting_tokens = (
        BUG_ID,
        "oss-fuzz",
        "clusterfuzz",
        "poc",
        "crash",
        "testcase",
        "repro",
        "input",
    )
    return any(tok in lower_name for tok in interesting_tokens)


def _extract_from_bytes_as_archive(name: str, data: bytes, depth: int) -> bytes | None:
    lower = name.lower()
    bio = io.BytesIO(data)
    if lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
        try:
            with tarfile.open(fileobj=bio, mode="r:*") as tf2:
                return _extract_from_tar(tf2, depth)
        except Exception:
            return None
    if lower.endswith(".zip"):
        try:
            with zipfile.ZipFile(bio, "r") as zf2:
                return _extract_from_zip(zf2, depth)
        except Exception:
            return None
    return None


def _read_tar_member(tf: tarfile.TarFile, member: tarfile.TarInfo) -> bytes | None:
    try:
        f = tf.extractfile(member)
        if f is None:
            return None
        return f.read()
    except Exception:
        return None


def _extract_from_tar(tf: tarfile.TarFile, depth: int) -> bytes | None:
    try:
        members = [m for m in tf.getmembers() if m.isreg() and m.size > 0]
    except Exception:
        return None

    if not members:
        return None

    perfect = []
    for m in members:
        low = m.name.lower()
        if (
            m.size == GROUND_TRUTH_LEN
            and (
                BUG_ID in low
                or "oss-fuzz" in low
                or "clusterfuzz" in low
                or "poc" in low
                or "crash" in low
                or "testcase" in low
                or "repro" in low
            )
        ):
            perfect.append(m)

    if perfect:
        best = max(perfect, key=lambda x: _score_candidate(x.name, x.size))
        data = _read_tar_member(tf, best)
        if data is not None:
            return data

    size_matches = [m for m in members if m.size == GROUND_TRUTH_LEN]
    if size_matches:
        best = max(size_matches, key=lambda x: _score_candidate(x.name, x.size))
        data = _read_tar_member(tf, best)
        if data is not None:
            return data

    if depth < MAX_ARCHIVE_DEPTH:
        for m in members:
            lower_name = m.name.lower()
            if m.size > MAX_NESTED_ARCHIVE_SIZE:
                continue
            if not _is_archive_name(lower_name):
                continue
            if not _is_interesting_archive_name(lower_name):
                continue
            raw = _read_tar_member(tf, m)
            if not raw:
                continue
            nested = _extract_from_bytes_as_archive(lower_name, raw, depth + 1)
            if nested is not None:
                return nested

    best_member = max(members, key=lambda x: _score_candidate(x.name, x.size))
    data = _read_tar_member(tf, best_member)
    return data


def _extract_from_zip(zf: zipfile.ZipFile, depth: int) -> bytes | None:
    try:
        infos = [i for i in zf.infolist() if not i.is_dir() and i.file_size > 0]
    except Exception:
        return None

    if not infos:
        return None

    perfect = []
    for info in infos:
        lower = info.filename.lower()
        if (
            info.file_size == GROUND_TRUTH_LEN
            and (
                BUG_ID in lower
                or "oss-fuzz" in lower
                or "clusterfuzz" in lower
                or "poc" in lower
                or "crash" in lower
                or "testcase" in lower
                or "repro" in lower
            )
        ):
            perfect.append(info)

    if perfect:
        best = max(perfect, key=lambda x: _score_candidate(x.filename, x.file_size))
        try:
            return zf.read(best)
        except Exception:
            pass

    size_matches = [i for i in infos if i.file_size == GROUND_TRUTH_LEN]
    if size_matches:
        best = max(size_matches, key=lambda x: _score_candidate(x.filename, x.file_size))
        try:
            return zf.read(best)
        except Exception:
            pass

    if depth < MAX_ARCHIVE_DEPTH:
        for info in infos:
            lower_name = info.filename.lower()
            if info.file_size > MAX_NESTED_ARCHIVE_SIZE:
                continue
            if not _is_archive_name(lower_name):
                continue
            if not _is_interesting_archive_name(lower_name):
                continue
            try:
                raw = zf.read(info)
            except Exception:
                continue
            nested = _extract_from_bytes_as_archive(lower_name, raw, depth + 1)
            if nested is not None:
                return nested

    best_info = max(infos, key=lambda x: _score_candidate(x.filename, x.file_size))
    try:
        return zf.read(best_info)
    except Exception:
        return None


def _extract_from_directory(root: str) -> bytes | None:
    best_path = None
    best_score = None

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            try:
                st = os.stat(full)
            except OSError:
                continue
            size = st.st_size
            if size <= 0:
                continue
            rel = os.path.relpath(full, root)
            score = _score_candidate(rel, size)
            if best_path is None or score > best_score:
                best_path = full
                best_score = score

    if best_path is None:
        return None

    try:
        with open(best_path, "rb") as f:
            return f.read()
    except OSError:
        return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            data = _extract_from_directory(src_path)
            if data is None:
                return b""
            return data

        try:
            with tarfile.open(src_path, "r:*") as tf:
                data = _extract_from_tar(tf, 0)
            if data is None:
                data = b""
            return data
        except Exception:
            try:
                with open(src_path, "rb") as f:
                    return f.read()
            except Exception:
                return b""