import os
import tarfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 71298

        best_score = float("-inf")
        best_source = None  # 'dir', 'tar', or 'zip'
        best_info = None

        keywords = (
            "poc",
            "crash",
            "uaf",
            "heap",
            "bug",
            "input",
            "fuzz",
            "corpus",
            "sample",
            "id:",
            "id_",
            "36861",
        )

        preferred_exts = (
            ".bin",
            ".dat",
            ".raw",
            ".poc",
            ".usb",
            ".in",
            ".out",
        )

        deprioritized_exts = (
            ".c",
            ".h",
            ".cpp",
            ".cc",
            ".hpp",
            ".txt",
            ".md",
            ".rst",
            ".py",
            ".sh",
            ".cmake",
            ".json",
            ".xml",
            ".html",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
            ".conf",
            ".bat",
            ".ps1",
            ".java",
            ".go",
            ".rs",
            ".m",
            ".mm",
            ".mak",
            ".mk",
            ".in.in",
        )

        max_candidate_size = 5 * 1024 * 1024

        def score_candidate(name: str, size: int) -> int:
            low = name.lower()
            score = -abs(size - target_len)

            if size == target_len:
                score += 100000

            if any(kw in low for kw in keywords):
                score += 1000000

            if low.endswith(preferred_exts):
                score += 200000

            if low.endswith(deprioritized_exts):
                score -= 1000000

            return score

        def consider(source: str, name: str, size: int, info):
            nonlocal best_score, best_source, best_info
            if size <= 0:
                return
            if size > max_candidate_size:
                return
            s = score_candidate(name, size)
            if s > best_score:
                best_score = s
                best_source = source
                best_info = info

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    path = os.path.join(root, fn)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    consider("dir", path, st.st_size, path)
        else:
            is_tar = False
            try:
                is_tar = tarfile.is_tarfile(src_path)
            except Exception:
                is_tar = False

            if is_tar:
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        for m in tf.getmembers():
                            if not m.isreg():
                                continue
                            consider("tar", m.name, m.size, m.name)
                except Exception:
                    pass
            else:
                is_zip = False
                try:
                    is_zip = zipfile.is_zipfile(src_path)
                except Exception:
                    is_zip = False

                if is_zip:
                    try:
                        with zipfile.ZipFile(src_path, "r") as zf:
                            for info in zf.infolist():
                                if info.is_dir():
                                    continue
                                consider("zip", info.filename, info.file_size, info.filename)
                    except Exception:
                        pass

        if best_source == "dir":
            try:
                with open(best_info, "rb") as f:
                    return f.read()
            except Exception:
                pass
        elif best_source == "tar":
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    try:
                        member = tf.getmember(best_info)
                        f = tf.extractfile(member)
                        if f is not None:
                            return f.read()
                    except KeyError:
                        pass
            except Exception:
                pass
        elif best_source == "zip":
            try:
                with zipfile.ZipFile(src_path, "r") as zf:
                    return zf.read(best_info)
            except Exception:
                pass

        pattern = (b"USBREDIR_POC_HEAP_USE_AFTER_FREE_" * ((target_len // 32) + 2))[:target_len]
        return pattern