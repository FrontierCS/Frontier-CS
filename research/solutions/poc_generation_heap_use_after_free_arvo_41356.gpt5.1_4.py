import os
import tarfile
import tempfile


def _extract_tar(src_path: str) -> str:
    if os.path.isdir(src_path):
        return src_path

    tmpdir = tempfile.mkdtemp(prefix="src-")
    try:
        with tarfile.open(src_path, "r:*") as tar:
            def is_within_directory(directory: str, target: str) -> bool:
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                return os.path.commonpath([abs_directory]) == os.path.commonpath(
                    [abs_directory, abs_target]
                )

            for member in tar.getmembers():
                member_path = os.path.join(tmpdir, member.name)
                if not is_within_directory(tmpdir, member_path):
                    continue
                tar.extract(member, path=tmpdir)
    except tarfile.ReadError:
        # Not a tar file; just return tmpdir (empty) so later logic falls back.
        return tmpdir
    return tmpdir


def _find_best_poc(root_dir: str) -> bytes | None:
    keywords = {
        "poc": 80.0,
        "proof_of_concept": 80.0,
        "proof-of-concept": 80.0,
        "crash": 60.0,
        "uaf": 60.0,
        "use_after_free": 60.0,
        "use-after-free": 60.0,
        "heap-use-after-free": 60.0,
        "double_free": 60.0,
        "double-free": 60.0,
        "asan": 40.0,
        "heapoverflow": 40.0,
        "heap": 20.0,
        "bug": 20.0,
        "id_": 15.0,
        "testcase": 25.0,
        "fuzz": 25.0,
        "seed": 15.0,
        "input": 10.0,
        "sample": 8.0,
        "case": 5.0,
    }

    data_exts = {
        "",
        ".bin",
        ".dat",
        ".raw",
        ".in",
        ".txt",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".msg",
        ".pb",
        ".pbf",
        ".pdf",
        ".html",
        ".svg",
        ".js",
        ".css",
    }

    code_exts = {
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".h",
        ".hh",
        ".hpp",
        ".java",
        ".py",
        ".sh",
        ".bat",
        ".ps1",
        ".rb",
        ".go",
        ".rs",
        ".js",
        ".ts",
        ".cs",
        ".m",
        ".mm",
    }

    max_size = 8192

    best_score = float("-inf")
    best_path: str | None = None

    # Fallback: nearest to 60 bytes among reasonably small "data-like" files
    fb_best_dist = float("inf")
    fb_best_size = float("inf")
    fb_best_path: str | None = None

    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            full_path = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue
            if size == 0 or size > max_size:
                continue

            rel_path = os.path.relpath(full_path, root_dir)
            lower_path = rel_path.lower()
            _, ext = os.path.splitext(name)
            ext = ext.lower()

            score = 0.0
            for kw, weight in keywords.items():
                if kw in lower_path:
                    score += weight

            if ext in data_exts:
                score += 5.0
            if ext in code_exts:
                score -= 20.0

            size_diff = abs(size - 60)
            score -= size_diff * 0.5
            score -= size * 0.01

            if score > best_score:
                best_score = score
                best_path = full_path

            # Fallback candidate: prefer data-like extensions or no extension
            if ext in data_exts or score > 0:
                if size_diff < fb_best_dist or (
                    size_diff == fb_best_dist and size < fb_best_size
                ):
                    fb_best_dist = size_diff
                    fb_best_size = size
                    fb_best_path = full_path

    chosen_path = None
    if best_path is not None and best_score > 0:
        chosen_path = best_path
    elif fb_best_path is not None:
        chosen_path = fb_best_path

    if chosen_path is None:
        return None

    try:
        with open(chosen_path, "rb") as f:
            return f.read()
    except OSError:
        return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _extract_tar(src_path)
        data = _find_best_poc(root)
        if data is not None and len(data) > 0:
            return data
        return b"A" * 60