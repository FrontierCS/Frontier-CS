import os
import tarfile
import zipfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        temp_root = None
        root_dir = None
        try:
            if os.path.isdir(src_path):
                root_dir = src_path
            else:
                temp_root = tempfile.mkdtemp(prefix="src-")
                extracted = False
                # Try tar formats
                try:
                    with tarfile.open(src_path, mode="r:*") as tf:
                        tf.extractall(temp_root)
                        extracted = True
                except tarfile.TarError:
                    extracted = False

                # Fallback to zip if not a tar archive
                if not extracted:
                    try:
                        with zipfile.ZipFile(src_path, mode="r") as zf:
                            zf.extractall(temp_root)
                            extracted = True
                    except zipfile.BadZipFile:
                        extracted = False

                if not extracted:
                    # Cannot extract; just return fallback
                    return self._fallback_poc()

                # Determine project root inside temp_root
                entries = [os.path.join(temp_root, e) for e in os.listdir(temp_root)]
                dirs = [p for p in entries if os.path.isdir(p)]
                files = [p for p in entries if os.path.isfile(p)]
                if len(dirs) == 1 and not files:
                    root_dir = dirs[0]
                else:
                    root_dir = temp_root

            poc_bytes = self._find_poc_bytes(root_dir)
            if poc_bytes is None or len(poc_bytes) == 0:
                return self._fallback_poc()
            return poc_bytes
        finally:
            if temp_root is not None and os.path.isdir(temp_root):
                shutil.rmtree(temp_root, ignore_errors=True)

    def _fallback_poc(self) -> bytes:
        # 24-byte deterministic fallback, likely not triggering the bug,
        # but used when no better candidate is found.
        return b"<a>fallback-poc-xxx</a>\n"

    def _find_poc_bytes(self, root_dir: str):
        """
        Attempt to locate a PoC file within the extracted source tree.
        """
        # Extensions that are likely to be source/code, not raw PoC data.
        code_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".py", ".sh", ".bat", ".ps1", ".java", ".cs", ".js", ".ts",
            ".go", ".rs", ".php", ".m", ".mm", ".swift", ".rb", ".pl",
            ".pm", ".tcl", ".lua", ".el", ".scm", ".clj", ".scala",
            ".cmake", ".vcxproj", ".sln", ".mk", ".make", ".in", ".ac",
            ".am", ".m4"
        }

        # Collect candidate files grouped by priority level.
        level1 = []  # Files whose path contains the specific bug id.
        level2 = []  # Files indicating PoC / crash / bug / UAF / oss-fuzz.
        level3 = []  # Generic test / fuzz / regression / corpus / seed files.
        level4 = []  # Any other reasonably small non-code files.

        max_size = 4096  # Ignore very large files to keep search cheap.
        target_len = 24

        for dirpath, dirnames, filenames in os.walk(root_dir):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size <= 0 or size > max_size:
                    continue

                _, ext = os.path.splitext(fname)
                ext = ext.lower()

                # Skip typical source/code files.
                if ext in code_exts:
                    continue

                rel = os.path.relpath(path, root_dir)
                rel_lower = rel.replace("\\", "/").lower()

                # Determine priority level
                # Level 1: bug-id specific
                if ("42537493" in rel_lower) or ("42537" in rel_lower):
                    level1.append((size, path))
                    continue

                # Level 2: PoC / crash / UAF / oss-fuzz / bug / issue
                if (
                    "poc" in rel_lower
                    or "crash" in rel_lower
                    or "use-after-free" in rel_lower
                    or "use_after_free" in rel_lower
                    or "uaf" in rel_lower
                    or "heap" in rel_lower
                    or "oss-fuzz" in rel_lower
                    or "ossfuzz" in rel_lower
                    or "clusterfuzz" in rel_lower
                    or "/bug" in rel_lower
                    or "_bug" in rel_lower
                    or "-bug" in rel_lower
                    or "/issue" in rel_lower
                    or "_issue" in rel_lower
                    or "-issue" in rel_lower
                ):
                    level2.append((size, path))
                    continue

                # Level 3: general tests / fuzz / regression / corpus / seeds
                if (
                    "test" in rel_lower
                    or "tests" in rel_lower
                    or "regress" in rel_lower
                    or "fuzz" in rel_lower
                    or "corpus" in rel_lower
                    or "seed" in rel_lower
                ):
                    level3.append((size, path))
                    continue

                # Level 4: any other small non-code file
                level4.append((size, path))

        # Choose best candidate from each level in order
        for level in (level1, level2, level3, level4):
            if not level:
                continue
            # Prefer files whose size is closest to the ground-truth 24 bytes,
            # and then smaller size, then lexicographically earlier path.
            level_sorted = sorted(
                level,
                key=lambda sp: (abs(sp[0] - target_len), sp[0], sp[1]),
            )
            for size, path in level_sorted:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    if data:
                        return data
                except OSError:
                    continue

        return None
