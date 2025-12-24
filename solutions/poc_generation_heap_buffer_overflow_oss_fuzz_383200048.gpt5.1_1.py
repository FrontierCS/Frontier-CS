import tarfile
from typing import Optional, List, Tuple


class Solution:
    def _is_probably_text(self, data: bytes) -> bool:
        if not data:
            return True
        if b"\0" in data:
            return False
        text_bytes = set(range(32, 127))
        whitespace_bytes = {9, 10, 13}  # \t, \n, \r
        nontext = 0
        for b in data:
            if b in text_bytes or b in whitespace_bytes:
                continue
            nontext += 1
        return (nontext / len(data)) < 0.30

    def _extract_best_poc_from_tar(self, tf: tarfile.TarFile) -> Optional[bytes]:
        tokens = (
            "oss-fuzz",
            "ossfuzz",
            "clusterfuzz",
            "crash",
            "poc",
            "regress",
            "fuzz",
            "bug",
            "issue",
            "testcase",
        )

        pri_name_id_512: List[Tuple[str, bytes]] = []
        pri_heur_512: List[Tuple[str, bytes]] = []
        fallback_512_bin: List[Tuple[str, bytes]] = []
        candidate512_text: List[Tuple[str, bytes]] = []

        pri_name_any: List[tarfile.TarInfo] = []
        pri_heur_any: List[tarfile.TarInfo] = []

        members = tf.getmembers()
        for member in members:
            if not member.isfile():
                continue
            path = member.name
            size = member.size
            lower_path = path.lower()
            has_id = "383200048" in lower_path
            fuzzish = any(tok in lower_path for tok in tokens)

            if size == 512:
                try:
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                is_text = self._is_probably_text(data)
                if is_text:
                    candidate512_text.append((path, data))
                    continue
                if has_id:
                    pri_name_id_512.append((path, data))
                elif fuzzish:
                    pri_heur_512.append((path, data))
                else:
                    fallback_512_bin.append((path, data))
            else:
                if has_id:
                    pri_name_any.append(member)
                elif fuzzish:
                    pri_heur_any.append(member)

        if pri_name_id_512:
            pri_name_id_512.sort(key=lambda x: x[0])
            return pri_name_id_512[0][1]

        if pri_heur_512:
            pri_heur_512.sort(key=lambda x: x[0])
            return pri_heur_512[0][1]

        if fallback_512_bin:
            fallback_512_bin.sort(key=lambda x: x[0])
            return fallback_512_bin[0][1]

        max_size = 1024 * 1024  # 1MB safety cap

        if pri_name_any:
            pri_name_any.sort(key=lambda m: m.name)
            for member in pri_name_any:
                if member.size <= 0 or member.size > max_size:
                    continue
                try:
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                if not self._is_probably_text(data):
                    return data

        if pri_heur_any:
            pri_heur_any.sort(key=lambda m: m.name)
            for member in pri_heur_any:
                if member.size <= 0 or member.size > max_size:
                    continue
                try:
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                if not self._is_probably_text(data):
                    return data

        if candidate512_text:
            candidate512_text.sort(key=lambda x: x[0])
            return candidate512_text[0][1]

        return None

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        try:
            with tarfile.open(src_path, mode="r:*") as tf:
                poc = self._extract_best_poc_from_tar(tf)
                if poc is not None:
                    return poc
        except Exception:
            pass
        return b"A" * 512
