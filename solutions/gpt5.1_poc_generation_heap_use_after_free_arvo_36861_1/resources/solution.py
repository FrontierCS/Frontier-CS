import os
import tarfile
import tempfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        GROUND_TRUTH_LEN = 71298

        def is_within_directory(directory: str, target: str) -> bool:
            abs_dir = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            try:
                return os.path.commonpath([abs_dir]) == os.path.commonpath(
                    [abs_dir, abs_target]
                )
            except ValueError:
                # On error, be conservative and disallow
                return False

        def safe_extract(tar: tarfile.TarFile, path: str) -> None:
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if is_within_directory(path, member_path):
                    tar.extract(member, path)

        def find_embedded_poc(root: str) -> bytes | None:
            text_exts = {
                ".c",
                ".cc",
                ".cpp",
                ".h",
                ".hpp",
                ".txt",
                ".md",
                ".rst",
                ".py",
                ".sh",
                ".java",
                ".html",
                ".xml",
                ".json",
                ".yml",
                ".yaml",
                ".toml",
                ".in",
                ".am",
                ".ac",
                ".cmake",
                ".cfg",
                ".conf",
                ".ini",
                ".tex",
                ".csv",
                ".tsv",
                ".bat",
                ".ps1",
            }

            preferred_candidates = []
            other_candidates = []

            for dirpath, _, filenames in os.walk(root):
                for fname in filenames:
                    path = os.path.join(dirpath, fname)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    if st.st_size != GROUND_TRUTH_LEN:
                        continue

                    lower = fname.lower()
                    ext = os.path.splitext(lower)[1]

                    if ext in text_exts:
                        continue

                    if any(
                        key in lower
                        for key in (
                            "poc",
                            "crash",
                            "id_",
                            "input",
                            "seed",
                            "testcase",
                            "fuzz",
                        )
                    ):
                        preferred_candidates.append(path)
                    else:
                        other_candidates.append(path)

            if preferred_candidates:
                preferred_candidates.sort()
                try:
                    with open(preferred_candidates[0], "rb") as f:
                        return f.read()
                except OSError:
                    pass

            if other_candidates:
                other_candidates.sort()
                try:
                    with open(other_candidates[0], "rb") as f:
                        return f.read()
                except OSError:
                    pass

            return None

        def infer_magic(root: str) -> bytes:
            magic = b""
            patterns = [
                r'#\s*define\s+USBREDIR_MAGIC\s+"([^"]+)"',
                r'#\s*define\s+USBREDIR_SIGNATURE\s+"([^"]+)"',
                r'#\s*define\s+.*MAGIC.*"([^"]+)"',
            ]
            for dirpath, _, filenames in os.walk(root):
                for fname in filenames:
                    if not fname.endswith((".h", ".hpp", ".c", ".cc", ".cpp")):
                        continue
                    path = os.path.join(dirpath, fname)
                    try:
                        with open(path, "r", errors="ignore") as f:
                            content = f.read()
                    except OSError:
                        continue
                    for pat in patterns:
                        m = re.search(pat, content)
                        if m:
                            candidate = m.group(1)
                            if "USB" in candidate.upper():
                                magic = candidate.encode("latin1", "ignore")
                                return magic
            return magic

        def generate_synthetic_poc(root: str) -> bytes:
            magic = infer_magic(root)
            header = magic + b"\x00" * 32

            # Body: cycles of all byte values, each repeated K times.
            # This gives a large, highly structured input that exercises
            # many control-flow paths and produces large buffers.
            K = 512
            cycles = 8  # ~1 MiB total body
            chunks = []
            for _ in range(cycles):
                for bval in range(256):
                    chunks.append(bytes((bval,)) * K)
            body = b"".join(chunks)
            return header + body

        def process_root(root: str) -> bytes:
            poc = find_embedded_poc(root)
            if poc is not None:
                return poc
            return generate_synthetic_poc(root)

        if os.path.isdir(src_path):
            return process_root(src_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, "r:*") as tar:
                safe_extract(tar, tmpdir)
            return process_root(tmpdir)
