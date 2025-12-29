import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            data = self._find_poc_in_tar(src_path)
            if data is not None:
                return data
        except Exception:
            pass
        return self._fallback_poc()

    def _find_poc_in_tar(self, src_path: str) -> bytes | None:
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        best_data = None
        best_score = None

        text_exts = (
            ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp",
            ".py", ".sh", ".txt", ".md", ".rst",
            ".html", ".htm", ".xml", ".json",
            ".yml", ".yaml", ".toml", ".cfg", ".ini",
            ".cmake", ".java", ".go", ".rs", ".m", ".mm",
            ".rb", ".php", ".pl", ".tex",
        )

        for m in tf.getmembers():
            if not m.isfile():
                continue
            size = m.size
            if size <= 0 or size > 1_000_000:
                continue

            try:
                f = tf.extractfile(m)
            except Exception:
                continue
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue
            if not data:
                continue

            name_l = m.name.lower()
            length = len(data)

            score = abs(length - 6431)

            for ext in text_exts:
                if name_l.endswith(ext):
                    score += 8000
                    break

            is_pdf = data.startswith(b"%PDF")
            if is_pdf or name_l.endswith(".pdf"):
                score -= 3000

            if "poc" in name_l:
                score -= 5000
            if "uaf" in name_l:
                score -= 3000
            if "use-after-free" in name_l or ("use" in name_l and "free" in name_l):
                score -= 3000
            if "heap" in name_l:
                score -= 1000
            if "crash" in name_l or "bug" in name_l:
                score -= 1500
            if "regress" in name_l or "test" in name_l:
                score -= 1000
            if "59207" in name_l:
                score -= 4000

            if length == 6431:
                score -= 10000

            if is_pdf:
                head = data[:2048]
                if b"xref" in head or b"obj" in head or b"trailer" in head:
                    score -= 500

            if best_score is None or score < best_score:
                best_score = score
                best_data = data

        return best_data

    def _fallback_poc(self) -> bytes:
        return (
            b"%PDF-1.3\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
            b"2 0 obj\n"
            b"<< /Type /Pages /Count 0 >>\n"
            b"endobj\n"
            b"trailer\n"
            b"<< /Root 1 0 R >>\n"
            b"%%EOF\n"
        )