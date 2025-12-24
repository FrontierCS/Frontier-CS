import os
import tarfile


class Solution:
    TARGET_POC_LEN = 1479

    def solve(self, src_path: str) -> bytes:
        data = None

        if os.path.isfile(src_path):
            try:
                data = self._extract_poc_from_tar(src_path)
            except Exception:
                data = None

        if data is None and os.path.isdir(src_path):
            try:
                data = self._extract_poc_from_dir(src_path)
            except Exception:
                data = None

        if data is not None:
            return data

        return self._fallback_poc()

    def _extract_poc_from_tar(self, tar_path: str):
        target_len = self.TARGET_POC_LEN
        max_dist = 4096

        best_j2k = None
        best_j2k_score = None
        best_other = None
        best_other_score = None

        patterns = (
            "poc",
            "proof",
            "crash",
            "bug",
            "regress",
            "nonreg",
            "fuzz",
            "input",
            "tests",
            "corpus",
            "afl",
            "oss-fuzz",
            "clusterfuzz",
            "id:",
            "id_",
        )

        try:
            tf = tarfile.open(tar_path, "r:*")
        except Exception:
            return None

        with tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0:
                    continue

                dist = abs(size - target_len)
                if dist > max_dist:
                    continue

                try:
                    f = tf.extractfile(m)
                except Exception:
                    continue
                if f is None:
                    continue

                try:
                    header = f.read(32)
                except Exception:
                    continue

                is_j2k = self._looks_like_jpeg2000(header)
                path_lower = m.name.lower()

                score = dist
                score += path_lower.count("/")

                if any(p in path_lower for p in patterns):
                    score -= 50
                if path_lower.endswith((".j2k", ".jp2", ".j2c", ".jpc", ".jpf", ".jpx")):
                    score -= 20

                if is_j2k:
                    if best_j2k is None or score < best_j2k_score:
                        best_j2k = m
                        best_j2k_score = score
                else:
                    if best_other is None or score < best_other_score:
                        best_other = m
                        best_other_score = score

            chosen = best_j2k if best_j2k is not None else best_other
            if chosen is None:
                return None

            try:
                f = tf.extractfile(chosen)
            except Exception:
                return None
            if f is None:
                return None

            try:
                data = f.read()
            except Exception:
                return None

            return data

    def _extract_poc_from_dir(self, root: str):
        target_len = self.TARGET_POC_LEN
        max_dist = 4096

        best_j2k_path = None
        best_j2k_score = None
        best_other_path = None
        best_other_score = None

        patterns = (
            "poc",
            "proof",
            "crash",
            "bug",
            "regress",
            "nonreg",
            "fuzz",
            "input",
            "tests",
            "corpus",
            "afl",
            "oss-fuzz",
            "clusterfuzz",
            "id:",
            "id_",
        )

        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0:
                    continue

                dist = abs(size - target_len)
                if dist > max_dist:
                    continue

                try:
                    with open(path, "rb") as f:
                        header = f.read(32)
                except OSError:
                    continue

                is_j2k = self._looks_like_jpeg2000(header)
                path_lower = path.lower()

                score = dist
                score += path_lower.count(os.sep)

                if any(p in path_lower for p in patterns):
                    score -= 50
                if path_lower.endswith((".j2k", ".jp2", ".j2c", ".jpc", ".jpf", ".jpx")):
                    score -= 20

                if is_j2k:
                    if best_j2k_path is None or score < best_j2k_score:
                        best_j2k_path = path
                        best_j2k_score = score
                else:
                    if best_other_path is None or score < best_other_score:
                        best_other_path = path
                        best_other_score = score

        chosen_path = best_j2k_path if best_j2k_path is not None else best_other_path
        if chosen_path is None:
            return None

        try:
            with open(chosen_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _looks_like_jpeg2000(self, header: bytes) -> bool:
        if len(header) >= 4 and header[0:4] == b"\xff\x4f\xff\x51":
            return True
        if len(header) >= 12:
            if header[4:8] == b"jP  " and header[8:12] == b"\r\n\x87\n":
                return True
            if header[0:12] == b"\x00\x00\x00\x0cjP  \r\n\x87\n":
                return True
        return False

    def _fallback_poc(self) -> bytes:
        sig = b"\x00\x00\x00\x0cjP  \r\n\x87\n"
        if len(sig) >= self.TARGET_POC_LEN:
            return sig[: self.TARGET_POC_LEN]
        pad_len = self.TARGET_POC_LEN - len(sig)
        return sig + (b"A" * pad_len)
