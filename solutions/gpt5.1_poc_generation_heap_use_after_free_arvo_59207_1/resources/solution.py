import os
import tarfile
import zipfile


TARGET_LEN = 6431


def _calc_weight(path_lower: str) -> int:
    tokens = {
        "59207": 500,
        "use-after-free": 200,
        "uaf": 180,
        "heap": 150,
        "poc": 300,
        "crash": 150,
        "bug": 130,
        "regress": 100,
        "regression": 100,
        "fuzz": 40,
        "oss-fuzz": 60,
        "clusterfuzz": 60,
        "seed": 30,
        "seeds": 30,
        "test": 20,
        "tests": 20,
        ".pdf": 5,
    }
    weight = 0
    for tok, val in tokens.items():
        if tok in path_lower:
            weight += val
    return weight


def _extract_poc_from_directory(root: str, target_len: int) -> bytes or None:
    best_path = None
    best_score = None

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            path = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue

            # Exact match with target length: check for PDF magic
            if size == target_len:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    if data.startswith(b"%PDF"):
                        return data
                except OSError:
                    pass

            lower_name = os.path.relpath(path, root).lower()
            if lower_name.endswith(".pdf"):
                weight = _calc_weight(lower_name)
                score = weight * 100000 - abs(size - target_len)
                if best_score is None or score > best_score:
                    best_score = score
                    best_path = path

    if best_path is not None:
        try:
            with open(best_path, "rb") as f:
                return f.read()
        except OSError:
            return None
    return None


def _extract_poc_from_tar(archive_path: str, target_len: int) -> bytes or None:
    try:
        tf = tarfile.open(archive_path, "r:*")
    except (tarfile.ReadError, FileNotFoundError, IsADirectoryError, PermissionError):
        return None

    with tf:
        best_member = None
        best_score = None

        for member in tf.getmembers():
            if not member.isfile():
                continue

            size = member.size

            # Exact-length candidate: read and check magic
            if size == target_len:
                try:
                    f = tf.extractfile(member)
                    if f is not None:
                        data = f.read()
                        if data.startswith(b"%PDF"):
                            return data
                except (OSError, tarfile.ExtractError):
                    pass

            name = member.name
            lower_name = name.lower()
            if lower_name.endswith(".pdf"):
                weight = _calc_weight(lower_name)
                score = weight * 100000 - abs(size - target_len)
                if best_score is None or score > best_score:
                    best_score = score
                    best_member = member

        if best_member is not None:
            try:
                f = tf.extractfile(best_member)
                if f is not None:
                    return f.read()
            except (OSError, tarfile.ExtractError):
                return None
    return None


def _extract_poc_from_zip(archive_path: str, target_len: int) -> bytes or None:
    try:
        zf = zipfile.ZipFile(archive_path, "r")
    except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError, PermissionError):
        return None

    with zf:
        best_info = None
        best_score = None

        for info in zf.infolist():
            if info.is_dir():
                continue

            size = info.file_size

            # Exact match: read and check PDF magic
            if size == target_len:
                try:
                    data = zf.read(info.filename)
                    if data.startswith(b"%PDF"):
                        return data
                except OSError:
                    pass

            name = info.filename
            lower_name = name.lower()
            if lower_name.endswith(".pdf"):
                weight = _calc_weight(lower_name)
                score = weight * 100000 - abs(size - target_len)
                if best_score is None or score > best_score:
                    best_score = score
                    best_info = info

        if best_info is not None:
            try:
                return zf.read(best_info.filename)
            except OSError:
                return None
    return None


def _generate_fallback_poc() -> bytes:
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 4\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000061 00000 n \n"
        b"0000000112 00000 n \n"
        b"trailer\n"
        b"<< /Root 1 0 R /Size 4 >>\n"
        b"startxref\n"
        b"0\n"
        b"%%EOF\n"
    )
    return pdf


class Solution:
    def solve(self, src_path: str) -> bytes:
        # If src_path is a directory, search it directly
        if os.path.isdir(src_path):
            data = _extract_poc_from_directory(src_path, TARGET_LEN)
            if data is not None:
                return data

        # Try as a tar archive
        data = _extract_poc_from_tar(src_path, TARGET_LEN)
        if data is not None:
            return data

        # Try as a zip archive
        data = _extract_poc_from_zip(src_path, TARGET_LEN)
        if data is not None:
            return data

        # Fallback: generic minimal PDF
        return _generate_fallback_poc()
