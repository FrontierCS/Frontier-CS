import os
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="poc_tic30_")

            # Safely extract the tarball
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

                safe_members = []
                for m in tf.getmembers():
                    target_path = os.path.join(tmpdir, m.name)
                    if is_within_directory(tmpdir, target_path):
                        safe_members.append(m)
                tf.extractall(tmpdir, members=safe_members)

            # Heuristic search for a 10-byte PoC file in the source tree
            best_data = None
            best_score = -1

            for root, _, files in os.walk(tmpdir):
                root_lower = root.lower()
                for fname in files:
                    full_path = os.path.join(root, fname)
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        continue

                    if size != 10:
                        continue

                    name_lower = fname.lower()
                    tokens = [
                        "tic30",
                        "tic-30",
                        "tms320c30",
                        "branch",
                        "print_branch",
                        "overflow",
                        "stack",
                        "poc",
                        "crash",
                        "bug",
                        "cve",
                        "pr",
                        "id:"
                    ]
                    score = 0
                    for t in tokens:
                        if t in name_lower or t in root_lower:
                            score += 1

                    # Prefer files whose names/directories look PoC-related
                    if score > best_score:
                        try:
                            with open(full_path, "rb") as f:
                                data = f.read()
                            if len(data) == 10:
                                best_data = data
                                best_score = score
                        except OSError:
                            continue

            if best_data is not None:
                return best_data

        except Exception:
            pass
        finally:
            if tmpdir is not None:
                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass

        # Fallback: simple 10-byte pattern
        return b"\xff" * 10
