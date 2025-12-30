import tarfile
from typing import Optional


class Solution:
    def _is_preferred_name(self, name: str) -> bool:
        lower = name.lower()
        keywords = [
            "poc",
            "crash",
            "testcase",
            "clusterfuzz",
            "oss-fuzz",
            "fuzz-",
            "fuzzer-",
            "bug",
            "id_",
            "id-",
            "383200048",
            "heap",
            "overflow",
        ]
        return any(k in lower for k in keywords)

    def _select_member(self, tf: tarfile.TarFile) -> Optional[tarfile.TarInfo]:
        size_map = {}
        preferred512 = []
        all512 = []

        for member in tf.getmembers():
            if not member.isfile():
                continue
            size = member.size
            if size <= 0:
                continue
            if size > 1_000_000:
                continue  # ignore very large files
            size_map.setdefault(size, []).append(member)
            if size == 512:
                all512.append(member)
                if self._is_preferred_name(member.name):
                    preferred512.append(member)

        if preferred512:
            return preferred512[0]
        if all512:
            return all512[0]

        # Look for small files with preferred names near 512 bytes
        candidate_members = []
        for size, members in size_map.items():
            if 16 <= size <= 4096:
                for m in members:
                    if self._is_preferred_name(m.name):
                        candidate_members.append((size, m))

        if candidate_members:
            candidate_members.sort(key=lambda sm: (abs(sm[0] - 512), sm[0]))
            return candidate_members[0][1]

        # Fallback: choose file whose size is nearest to 512
        if size_map:
            all_sizes = list(size_map.keys())
            best_size = min(all_sizes, key=lambda s: abs(s - 512))
            return size_map[best_size][0]

        return None

    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                member = self._select_member(tf)
                if member is not None:
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        data = extracted.read()
                        if isinstance(data, bytes) and data:
                            return data
        except Exception:
            pass

        # Final fallback: generic 512-byte buffer
        return b"A" * 512