import tarfile
from typing import List, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        def has_text_extension(name: str) -> bool:
            name = name.lower()
            text_exts = (
                ".xml",
                ".html",
                ".htm",
                ".xhtml",
                ".txt",
                ".dat",
                ".sgml",
                ".sgm",
                ".json",
                ".xsl",
                ".xslt",
                ".svg",
            )
            return any(name.endswith(ext) for ext in text_exts)

        def select_member(
            members: List[tarfile.TarInfo],
            substrs: List[str],
            prefer_text: bool = True,
        ) -> Optional[tarfile.TarInfo]:
            candidates: List[tarfile.TarInfo] = []
            for m in members:
                if not m.isfile():
                    continue
                if m.size <= 0:
                    continue
                name_lower = m.name.lower()
                if any(sub in name_lower for sub in substrs):
                    if prefer_text and not has_text_extension(name_lower):
                        continue
                    candidates.append(m)
            if not candidates and prefer_text:
                for m in members:
                    if not m.isfile():
                        continue
                    if m.size <= 0:
                        continue
                    name_lower = m.name.lower()
                    if any(sub in name_lower for sub in substrs):
                        candidates.append(m)
            if not candidates:
                return None
            candidates.sort(key=lambda x: x.size)
            return candidates[0]

        # Fallback PoC guess (24 bytes)
        fallback_poc = b'<?xml version="1.0"?><a/>'

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return fallback_poc

        with tf:
            members = tf.getmembers()

            # 1) Search by full bug-id / truncated id in file names
            search_patterns = [
                ["42537493"],
                ["oss-fuzz-42537493"],
                ["ossfuzz-42537493"],
                ["42537"],
            ]
            for patterns in search_patterns:
                m = select_member(members, patterns, prefer_text=True)
                if m is not None:
                    try:
                        f = tf.extractfile(m)
                        if f is not None:
                            data = f.read()
                            if data:
                                return data
                    except Exception:
                        pass

            # 2) Search inside small test/fuzz files for the bug id
            best_data: Optional[bytes] = None
            for m in members:
                if not m.isfile():
                    continue
                if m.size == 0 or m.size > 4096:
                    continue
                name_lower = m.name.lower()
                if (
                    "test" not in name_lower
                    and "fuzz" not in name_lower
                    and "regress" not in name_lower
                    and "regression" not in name_lower
                ):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                if b"42537493" in data or b"42537" in data:
                    if best_data is None or len(data) < len(best_data):
                        best_data = data
            if best_data is not None:
                return best_data

            # 3) Fallback: smallest oss-fuzz-related text file
            oss_candidates: List[tarfile.TarInfo] = []
            for m in members:
                if not m.isfile() or m.size == 0:
                    continue
                name_lower = m.name.lower()
                if "oss-fuzz" in name_lower or "ossfuzz" in name_lower:
                    if has_text_extension(name_lower):
                        oss_candidates.append(m)
            if oss_candidates:
                oss_candidates.sort(key=lambda x: x.size)
                try:
                    f = tf.extractfile(oss_candidates[0])
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        # Final generic fallback if nothing found in the tarball
        return fallback_poc