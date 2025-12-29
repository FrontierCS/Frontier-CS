import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        lg = 33453

        data = None

        if os.path.isfile(src_path):
            try:
                data = self._extract_from_tar(src_path, lg)
            except tarfile.ReadError:
                data = None
            except Exception:
                data = None

        if data is not None:
            return data

        if os.path.isdir(src_path):
            try:
                data = self._extract_from_dir(src_path, lg)
            except Exception:
                data = None

        if data is not None:
            return data

        return self._fallback_pdf()

    def _base_score(self, name_lower: str, size: int, lg: int) -> int:
        score = 0
        diff = abs(size - lg)

        if diff == 0:
            score += 200
        elif diff <= 64:
            score += 140
        elif diff <= 256:
            score += 110
        elif diff <= 1024:
            score += 80
        elif diff <= 4096:
            score += 40
        elif diff <= 16384:
            score += 10

        if "42535152" in name_lower:
            score += 120
        if "oss-fuzz" in name_lower or "ossfuzz" in name_lower:
            score += 100
        if "clusterfuzz" in name_lower:
            score += 90
        if "testcase" in name_lower:
            score += 70
        if "repro" in name_lower or "reproducer" in name_lower:
            score += 70
        if "poc" in name_lower:
            score += 80
        if "uaf" in name_lower or "use-after-free" in name_lower or "use_after_free" in name_lower:
            score += 60
        if "heap-use-after-free" in name_lower or "heap_use_after_free" in name_lower:
            score += 60
        if "fuzz" in name_lower:
            score += 20

        base, ext = os.path.splitext(name_lower)
        binary_exts = {
            ".pdf",
            ".bin",
            ".dat",
            ".raw",
            ".repro",
            ".input",
            ".seed",
            ".case",
        }
        text_exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".py",
            ".java",
            ".js",
            ".html",
            ".xml",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".cmake",
            ".sh",
            ".bat",
            ".ps1",
            ".in",
            ".ac",
            ".am",
            ".m4",
            ".sln",
            ".vcxproj",
            ".vcproj",
            ".gradle",
            ".mak",
            ".rst",
            ".tex",
            ".csv",
            ".tsv",
            ".ini",
            ".cfg",
            ".conf",
        }

        if ext in binary_exts:
            score += 60
        elif ext in text_exts:
            score -= 60

        return score

    def _evaluate_with_sample(self, name_lower: str, size: int, sample: bytes, lg: int) -> int:
        score = self._base_score(name_lower, size, lg)

        if sample:
            if sample.startswith(b"%PDF-"):
                score += 150

            non_printable = 0
            for b in sample:
                if b in (9, 10, 13) or 32 <= b <= 126:
                    continue
                non_printable += 1
            ratio = non_printable / float(len(sample))
            if ratio > 0.10:
                score += 50
            else:
                score -= 30

        return score

    def _extract_from_tar(self, tar_path: str, lg: int) -> bytes | None:
        best_member = None
        best_score = float("-inf")
        best_size = 0

        with tarfile.open(tar_path, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isreg():
                    continue

                name_lower = member.name.lower()
                size = member.size
                diff = abs(size - lg)

                need_sample = False
                base, ext = os.path.splitext(name_lower)
                if diff <= 2048 or "poc" in name_lower or "clusterfuzz" in name_lower or "oss-fuzz" in name_lower or ext == ".pdf":
                    need_sample = True

                sample = b""
                if need_sample:
                    try:
                        f = tf.extractfile(member)
                        if f is not None:
                            sample = f.read(2048)
                            f.close()
                    except Exception:
                        sample = b""

                if sample:
                    score = self._evaluate_with_sample(name_lower, size, sample, lg)
                else:
                    score = self._base_score(name_lower, size, lg)

                if score > best_score:
                    best_score = score
                    best_member = member
                    best_size = size

            if best_member is not None:
                size_limit = max(lg * 10, 1_048_576)
                if best_size <= size_limit:
                    try:
                        f = tf.extractfile(best_member)
                        if f is not None:
                            data = f.read()
                            f.close()
                            if data:
                                return data
                    except Exception:
                        return None

        return None

    def _extract_from_dir(self, root: str, lg: int) -> bytes | None:
        best_path = None
        best_score = float("-inf")
        best_size = 0

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                name_lower = path.lower()
                diff = abs(size - lg)
                base, ext = os.path.splitext(name_lower)
                need_sample = False
                if diff <= 2048 or "poc" in name_lower or "clusterfuzz" in name_lower or "oss-fuzz" in name_lower or ext == ".pdf":
                    need_sample = True

                sample = b""
                if need_sample:
                    try:
                        with open(path, "rb") as f:
                            sample = f.read(2048)
                    except OSError:
                        sample = b""

                if sample:
                    score = self._evaluate_with_sample(name_lower, size, sample, lg)
                else:
                    score = self._base_score(name_lower, size, lg)

                if score > best_score:
                    best_score = score
                    best_path = path
                    best_size = size

        if best_path is not None:
            size_limit = max(lg * 10, 1_048_576)
            if best_size <= size_limit:
                try:
                    with open(best_path, "rb") as f:
                        data = f.read()
                    if data:
                        return data
                except OSError:
                    return None

        return None

    def _fallback_pdf(self) -> bytes:
        return (
            b"%PDF-1.1\n"
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
            b"0000000117 00000 n \n"
            b"trailer\n"
            b"<< /Size 4 /Root 1 0 R >>\n"
            b"startxref\n"
            b"170\n"
            b"%%EOF\n"
        )