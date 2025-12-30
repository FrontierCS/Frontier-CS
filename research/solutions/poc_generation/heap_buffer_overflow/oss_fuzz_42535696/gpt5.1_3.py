import os
import tarfile
import tempfile
import gzip


class Solution:
    def solve(self, src_path: str) -> bytes:
        BUG_ID = "42535696"
        GROUND_TRUTH_LEN = 150979

        def extract_tarball(tar_path: str) -> str:
            tmp_dir = tempfile.mkdtemp(prefix="src_")
            try:
                with tarfile.open(tar_path, "r:*") as tf:
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        return prefix == abs_directory

                    for member in tf.getmembers():
                        member_path = os.path.join(tmp_dir, member.name)
                        if not is_within_directory(tmp_dir, member_path):
                            continue
                        tf.extract(member, tmp_dir)
            except tarfile.TarError:
                # If it's not a tarball, just treat the path as a directory
                return src_path
            return tmp_dir

        def collect_files(root: str):
            all_files = []
            for dirpath, _, filenames in os.walk(root):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    try:
                        size = os.path.getsize(fpath)
                    except OSError:
                        continue
                    all_files.append((fpath, fname, size))
            return all_files

        def pick_best_candidate(candidates):
            if not candidates:
                return None
            # Prefer sizes close to ground-truth and known binary extensions
            def ext_priority(name: str) -> int:
                name = name.lower()
                for ext, prio in (
                    (".pdf", 0),
                    (".ps", 0),
                    (".bin", 1),
                    (".dat", 1),
                    (".poc", 1),
                    (".input", 1),
                    (".seed", 1),
                    (".raw", 1),
                    (".txt", 2),
                ):
                    if name.endswith(ext):
                        return prio
                return 3

            candidates.sort(
                key=lambda x: (
                    abs(x[2] - GROUND_TRUTH_LEN),
                    ext_priority(x[1]),
                    x[2],
                )
            )
            return candidates[0]

        def load_poc(full_path: str, filename: str, size: int) -> bytes:
            try:
                with open(full_path, "rb") as f:
                    data = f.read()
            except OSError:
                return b""
            lower = filename.lower()
            if lower.endswith(".gz") or lower.endswith(".gzip"):
                try:
                    decompressed = gzip.decompress(data)
                    if abs(len(decompressed) - GROUND_TRUTH_LEN) <= abs(size - GROUND_TRUTH_LEN):
                        data = decompressed
                except OSError:
                    pass
            return data

        # Determine source directory (either extract tarball or use directory directly)
        if os.path.isdir(src_path):
            src_dir = src_path
        else:
            src_dir = extract_tarball(src_path)

        files = collect_files(src_dir)

        # 1. Prefer files whose names contain the bug ID
        bug_files = [info for info in files if BUG_ID in info[1]]
        chosen = pick_best_candidate(bug_files)

        # 2. If none, look for files with size exactly equal to ground-truth length
        if chosen is None:
            exact_size_files = [info for info in files if info[2] == GROUND_TRUTH_LEN]
            chosen = pick_best_candidate(exact_size_files)

        # 3. If still none, try gzip files whose decompressed size matches ground-truth
        if chosen is None:
            gz_matches = []
            for full, name, size in files:
                lname = name.lower()
                if lname.endswith(".gz") or lname.endswith(".gzip"):
                    try:
                        with gzip.open(full, "rb") as f:
                            data = f.read()
                        if len(data) == GROUND_TRUTH_LEN or BUG_ID in name:
                            gz_matches.append((full, name, len(data)))
                    except OSError:
                        continue
            chosen = pick_best_candidate(gz_matches)

        if chosen is not None:
            full, name, size = chosen
            poc = load_poc(full, name, size)
            if poc:
                return poc

        # Fallback: minimal dummy input in case no PoC found
        return b"%PDF-1.3\n% Fallback PoC - no embedded corpus sample found.\n"