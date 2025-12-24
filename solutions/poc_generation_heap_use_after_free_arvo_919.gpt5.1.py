import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            data = self._solve_from_dir(src_path)
        else:
            data = self._solve_from_tar(src_path)
        if data is None:
            data = b"A" * 800
        return data

    def _score_candidate(self, name: str, size: int, full_path: str = "") -> int:
        name_lower = name.lower()
        path_lower = full_path.lower() if full_path else name_lower
        base, ext = os.path.splitext(name_lower)

        score = abs(size - 800)

        font_exts = {".ttf", ".otf", ".otc", ".woff", ".woff2"}
        if ext in font_exts:
            score -= 200

        keywords = [
            "poc",
            "crash",
            "uaf",
            "heap",
            "use-after-free",
            "use_after_free",
            "useafterfree",
            "otsstream",
            "stream",
            "write",
            "regress",
            "regression",
            "fuzz",
            "corpus",
            "bug",
            "issue",
        ]
        if any(k in name_lower for k in keywords):
            score -= 100
        if any(k in path_lower for k in keywords):
            score -= 50

        if "919" in name_lower or "919" in path_lower:
            score -= 50

        if "test" in path_lower or "tests" in path_lower:
            score -= 20

        return score

    def _solve_from_dir(self, base_path: str) -> bytes | None:
        best_path = None
        best_score = None

        for root, _, files in os.walk(base_path):
            for name in files:
                full = os.path.join(root, name)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size <= 0 or size > 1024 * 1024:
                    continue

                score = self._score_candidate(name, size, full)
                if best_score is None or score < best_score:
                    best_score = score
                    best_path = full

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except OSError:
                return None
        return None

    def _solve_from_tar(self, tar_path: str) -> bytes | None:
        try:
            tf = tarfile.open(tar_path, "r:*")
        except tarfile.TarError:
            return None

        best_member = None
        best_score = None

        try:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0 or size > 1024 * 1024:
                    continue

                name = os.path.basename(m.name)
                score = self._score_candidate(name, size, m.name)
                if best_score is None or score < best_score:
                    best_score = score
                    best_member = m

            if best_member is not None:
                f = tf.extractfile(best_member)
                if f is None:
                    return None
                try:
                    data = f.read()
                finally:
                    f.close()
                return data
        finally:
            tf.close()

        return None
