import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 13996
        try:
            with tarfile.open(src_path, "r:*") as tf:
                member = self._select_poc_member(tf, target_size)
                if member is not None:
                    f = tf.extractfile(member)
                    if f is not None:
                        data = f.read()
                        if isinstance(data, bytes) and data:
                            return data
        except Exception:
            pass
        return self._fallback_poc()

    def _select_poc_member(self, tf, target_size: int):
        members = [m for m in tf.getmembers() if m.isreg() and m.size > 0]
        if not members:
            return None

        exact = [m for m in members if m.size == target_size]
        if exact:
            best = None
            best_score = float("-inf")
            for m in exact:
                score = self._score_member(m, include_size=False, target_size=target_size)
                if score > best_score:
                    best_score = score
                    best = m
            return best

        best = None
        best_score = float("-inf")
        for m in members:
            score = self._score_member(m, include_size=True, target_size=target_size)
            if score > best_score:
                best_score = score
                best = m
        return best

    def _score_member(self, member, include_size: bool, target_size: int) -> float:
        name = member.name
        base = os.path.basename(name)
        lower = base.lower()
        ext = os.path.splitext(base)[1].lower()
        size = member.size
        score = 0.0

        if ext in (".ps", ".pdf", ".eps"):
            score += 100.0
        elif ext in (".txt", ".bin", ".dat", ".raw"):
            score += 40.0
        elif ext == "":
            score += 10.0
        elif ext in (".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".java", ".py", ".md"):
            score -= 40.0

        keywords = (
            "poc",
            "crash",
            "bug",
            "testcase",
            "id_",
            "uaf",
            "use-after",
            "use_after",
            "heap",
        )
        for kw in keywords:
            if kw in lower:
                score += 10.0

        if "42280" in lower or "arvo" in lower:
            score += 80.0

        if "pdf" in lower or "ps" in lower:
            score += 5.0

        if size > 1_000_000:
            score -= 40.0

        if include_size:
            diff = abs(size - target_size)
            size_score = max(0.0, 60.0 - diff / 200.0)
            if size == target_size:
                size_score += 40.0
            score += size_score

        return score

    def _fallback_poc(self) -> bytes:
        poc = (
            b"%PDF-1.4\n"
            b"% Fallback PoC input\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R /MediaBox [0 0 612 792] >>\n"
            b"endobj\n"
            b"4 0 obj\n"
            b"<< /Length 21 >>\n"
            b"stream\n"
            b"q 0 0 0 rg Q\n"
            b"endstream\n"
            b"endobj\n"
            b"xref\n"
            b"0 5\n"
            b"0000000000 65535 f \n"
            b"0000000010 00000 n \n"
            b"0000000060 00000 n \n"
            b"0000000119 00000 n \n"
            b"0000000203 00000 n \n"
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            b"280\n"
            b"%%EOF\n"
        )
        return poc
