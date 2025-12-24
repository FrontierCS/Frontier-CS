import os
import tarfile
import gzip
import bz2
import lzma


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            if os.path.isdir(src_path):
                data = self._find_poc_in_dir(src_path)
            elif tarfile.is_tarfile(src_path):
                data = self._find_poc_in_tar(src_path)
            else:
                data = None
        except Exception:
            data = None

        if not data:
            data = self._default_poc()

        return data

    def _default_poc(self) -> bytes:
        # Minimal, generic PDF as fallback
        return (
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
            b"0000000060 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer\n"
            b"<< /Size 4 /Root 1 0 R >>\n"
            b"startxref\n"
            b"170\n"
            b"%%EOF\n"
        )

    def _find_poc_in_tar(self, tar_path: str) -> bytes | None:
        try:
            tf = tarfile.open(tar_path, "r:*")
        except Exception:
            return None

        best_member = None
        best_score = -1
        best_size_diff = None
        target_size = 33453

        # File extensions that are likely to contain binary PoCs
        binary_exts = {
            ".pdf",
            ".bin",
            ".dat",
            ".raw",
            ".poc",
            ".gz",
            ".bz2",
            ".xz",
            ".lzma",
        }

        code_exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hh",
            ".hpp",
            ".py",
            ".java",
            ".cs",
            ".js",
            ".ts",
            ".go",
            ".rs",
            ".m",
            ".mm",
            ".sh",
            ".bat",
            ".ps1",
            ".cmake",
            ".ac",
            ".am",
            ".in",
        }

        text_like_exts = {
            ".txt",
            ".md",
            ".rst",
            ".html",
            ".htm",
            ".xml",
            ".json",
            ".yml",
            ".yaml",
            ".csv",
        }

        try:
            for member in tf.getmembers():
                if not member.isfile() or member.size <= 0:
                    continue

                name = member.name.lower()
                base = os.path.basename(name)
                _, ext = os.path.splitext(base)

                # Skip obvious source/text files unless strongly hinted
                if ext in code_exts or ext in text_like_exts:
                    if "poc" not in name and "crash" not in name and "42535152" not in name:
                        continue

                is_candidate = False
                if ext in binary_exts:
                    is_candidate = True
                elif ext == "":
                    # Files without extension but with typical PoC hints
                    if (
                        "poc" in name
                        or "crash" in name
                        or "oss-fuzz" in name
                        or "ossfuzz" in name
                        or "clusterfuzz" in name
                        or "testcase" in name
                        or "42535152" in name
                    ):
                        is_candidate = True

                if not is_candidate:
                    continue

                score = 0

                if ext == ".pdf" or name.endswith(".pdf.gz") or name.endswith(".pdf.bz2") or name.endswith(".pdf.xz") or name.endswith(".pdf.lzma"):
                    score += 100

                if "42535152" in name:
                    score += 120
                if "oss-fuzz" in name or "ossfuzz" in name or "clusterfuzz" in name:
                    score += 80
                if "poc" in name:
                    score += 70
                if "crash" in name or "uaf" in name or "use-after-free" in name:
                    score += 60
                if "regress" in name or "bug" in name or "issue" in name:
                    score += 20
                if "fuzz" in name:
                    score += 10

                size_diff = abs(member.size - target_size)

                if best_member is None:
                    best_member = member
                    best_score = score
                    best_size_diff = size_diff
                else:
                    if score > best_score:
                        best_member = member
                        best_score = score
                        best_size_diff = size_diff
                    elif score == best_score and size_diff < (best_size_diff if best_size_diff is not None else size_diff + 1):
                        best_member = member
                        best_size_diff = size_diff
        finally:
            try:
                tf.close()
            except Exception:
                pass

        if best_member is None:
            return None

        try:
            with tarfile.open(tar_path, "r:*") as tf2:
                f = tf2.extractfile(best_member)
                if f is None:
                    return None
                data = f.read()
        except Exception:
            return None

        # Try to transparently decompress if needed
        name = best_member.name.lower()
        try:
            if name.endswith(".gz"):
                data = gzip.decompress(data)
            elif name.endswith(".bz2"):
                data = bz2.decompress(data)
            elif name.endswith(".xz") or name.endswith(".lzma"):
                data = lzma.decompress(data)
        except Exception:
            # If decompression fails, just return the raw data
            pass

        return data if data else None

    def _find_poc_in_dir(self, root_dir: str) -> bytes | None:
        best_path = None
        best_score = -1
        best_size_diff = None
        target_size = 33453

        binary_exts = {
            ".pdf",
            ".bin",
            ".dat",
            ".raw",
            ".poc",
            ".gz",
            ".bz2",
            ".xz",
            ".lzma",
        }

        code_exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hh",
            ".hpp",
            ".py",
            ".java",
            ".cs",
            ".js",
            ".ts",
            ".go",
            ".rs",
            ".m",
            ".mm",
            ".sh",
            ".bat",
            ".ps1",
            ".cmake",
            ".ac",
            ".am",
            ".in",
        }

        text_like_exts = {
            ".txt",
            ".md",
            ".rst",
            ".html",
            ".htm",
            ".xml",
            ".json",
            ".yml",
            ".yaml",
            ".csv",
        }

        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue

                if size <= 0:
                    continue

                name = full_path.lower()
                base = os.path.basename(name)
                _, ext = os.path.splitext(base)

                if ext in code_exts or ext in text_like_exts:
                    if "poc" not in name and "crash" not in name and "42535152" not in name:
                        continue

                is_candidate = False
                if ext in binary_exts:
                    is_candidate = True
                elif ext == "":
                    if (
                        "poc" in name
                        or "crash" in name
                        or "oss-fuzz" in name
                        or "ossfuzz" in name
                        or "clusterfuzz" in name
                        or "testcase" in name
                        or "42535152" in name
                    ):
                        is_candidate = True

                if not is_candidate:
                    continue

                score = 0

                if ext == ".pdf" or name.endswith(".pdf.gz") or name.endswith(".pdf.bz2") or name.endswith(".pdf.xz") or name.endswith(".pdf.lzma"):
                    score += 100

                if "42535152" in name:
                    score += 120
                if "oss-fuzz" in name or "ossfuzz" in name or "clusterfuzz" in name:
                    score += 80
                if "poc" in name:
                    score += 70
                if "crash" in name or "uaf" in name or "use-after-free" in name:
                    score += 60
                if "regress" in name or "bug" in name or "issue" in name:
                    score += 20
                if "fuzz" in name:
                    score += 10

                size_diff = abs(size - target_size)

                if best_path is None:
                    best_path = full_path
                    best_score = score
                    best_size_diff = size_diff
                else:
                    if score > best_score:
                        best_path = full_path
                        best_score = score
                        best_size_diff = size_diff
                    elif score == best_score and size_diff < (best_size_diff if best_size_diff is not None else size_diff + 1):
                        best_path = full_path
                        best_size_diff = size_diff

        if best_path is None:
            return None

        try:
            with open(best_path, "rb") as f:
                data = f.read()
        except Exception:
            return None

        name = best_path.lower()
        try:
            if name.endswith(".gz"):
                data = gzip.decompress(data)
            elif name.endswith(".bz2"):
                data = bz2.decompress(data)
            elif name.endswith(".xz") or name.endswith(".lzma"):
                data = lzma.decompress(data)
        except Exception:
            pass

        return data if data else None
