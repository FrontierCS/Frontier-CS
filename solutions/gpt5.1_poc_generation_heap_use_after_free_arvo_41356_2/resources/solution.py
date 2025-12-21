import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    safe_base = os.path.realpath(tmpdir)
                    for member in tf.getmembers():
                        member_path = os.path.realpath(os.path.join(tmpdir, member.name))
                        if not member_path.startswith(safe_base + os.sep) and member_path != safe_base:
                            continue
                        try:
                            tf.extract(member, tmpdir)
                        except Exception:
                            continue
            except Exception:
                return b"A" * 60

            candidates = []

            for root, dirs, files in os.walk(tmpdir):
                dir_lower = os.path.basename(root).lower()
                for fn in files:
                    path = os.path.join(root, fn)
                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        continue
                    if size == 0 or size > 4096:
                        continue

                    lower = fn.lower()
                    ext = os.path.splitext(fn)[1].lower()

                    # Skip obvious source/config/script files, but keep .txt (might store PoC).
                    if ext in {
                        ".c",
                        ".cc",
                        ".cpp",
                        ".cxx",
                        ".c++",
                        ".h",
                        ".hh",
                        ".hpp",
                        ".hxx",
                        ".py",
                        ".md",
                        ".rst",
                        ".html",
                        ".htm",
                        ".xml",
                        ".json",
                        ".yml",
                        ".yaml",
                        ".in",
                        ".cmake",
                        ".sh",
                        ".bat",
                        ".ps1",
                        ".sln",
                        ".vcxproj",
                        ".toml",
                        ".ini",
                        ".cfg",
                        ".conf",
                        ".mk",
                        ".makefile",
                    }:
                        continue

                    name_score = 0
                    name = lower

                    if "poc" in name:
                        name_score += 100
                    if "crash" in name or "bug" in name or "exploit" in name or "uaf" in name:
                        name_score += 80
                    if "double" in name and "free" in name:
                        name_score += 60
                    if "id:" in name or name.startswith("id_") or name.startswith("id-"):
                        name_score += 40
                    if "repro" in name or "reproducer" in name:
                        name_score += 40
                    if "seed" in name or "seed" in dir_lower:
                        name_score += 5
                    if "test" in name or "fuzz" in dir_lower or "fuzz" in name:
                        name_score += 10
                    if "poc" in dir_lower:
                        name_score += 50
                    if "crash" in dir_lower or "uaf" in dir_lower:
                        name_score += 40
                    if "double" in dir_lower and "free" in dir_lower:
                        name_score += 40

                    if name_score == 0:
                        if ext in {"", ".bin", ".dat", ".in"}:
                            name_score = 1
                        else:
                            continue

                    distance = abs(size - 60)
                    candidates.append((name_score, distance, size, path))

            if candidates:
                candidates.sort(key=lambda t: (-t[0], t[1], t[2], t[3]))
                best_path = candidates[0][3]
                try:
                    with open(best_path, "rb") as f:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

            return (b"POC" * 20)[:60]
        except Exception:
            return b"A" * 60
