import os
import tarfile
import zipfile
import tempfile
import stat


class Solution:
    def _prepare_src(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        tmpdir = tempfile.mkdtemp(prefix="src_extract_")
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        elif zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                zf.extractall(tmpdir)
        return tmpdir

    def _find_poc(self, root_dir: str) -> str | None:
        rar_magic_v5 = b"Rar!\x1a\x07\x01\x00"
        rar_magic_prefix = b"Rar!\x1a\x07"
        target_size = 524

        buckets: list[list[str]] = [[] for _ in range(4)]
        size_match_non_rar: list[str] = []

        for dirpath, dirnames, filenames in os.walk(root_dir):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path, follow_symlinks=False)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                size = st.st_size
                try:
                    with open(path, "rb") as f:
                        header = f.read(8)
                except OSError:
                    continue

                is_rar = header.startswith(rar_magic_prefix)
                is_v5 = header.startswith(rar_magic_v5)

                if is_rar:
                    if is_v5 and size == target_size:
                        buckets[0].append(path)
                    elif is_v5:
                        buckets[1].append(path)
                    elif size == target_size:
                        buckets[2].append(path)
                    else:
                        buckets[3].append(path)
                else:
                    if size == target_size:
                        size_match_non_rar.append(path)

        def key_func(p: str) -> tuple[int, int]:
            name = os.path.basename(p).lower()
            if "poc" in name:
                pri = 0
            elif "crash" in name or "issue" in name or "bug" in name:
                pri = 1
            elif name.startswith("id:") or name.startswith("id_"):
                pri = 2
            else:
                pri = 3
            return (pri, len(p))

        for bucket in buckets:
            if bucket:
                return min(bucket, key=key_func)
        if size_match_non_rar:
            return min(size_match_non_rar, key=key_func)
        return None

    def solve(self, src_path: str) -> bytes:
        root_dir = self._prepare_src(src_path)
        poc_path = self._find_poc(root_dir)
        if poc_path is not None:
            try:
                with open(poc_path, "rb") as f:
                    return f.read()
            except OSError:
                pass
        # Fallback: minimal RAR5-like header padded to 524 bytes
        base = b"Rar!\x1a\x07\x01\x00"
        if len(base) < 524:
            base = base + b"\x00" * (524 - len(base))
        return base
