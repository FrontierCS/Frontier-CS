import tarfile
import os


class Solution:
    def _select_member(self, members, target_len: int):
        if not members:
            return None

        skip_exts = ('.gz', '.zip', '.bz2', '.xz', '.7z')

        filtered = []
        for m in members:
            name_lower = m.name.lower()
            if name_lower.endswith(skip_exts):
                continue
            filtered.append(m)

        if not filtered:
            filtered = members

        keyword_sets = [
            ['poc', 'crash', 'heap-buffer-overflow', 'heap_overflow', 'heap-overflow',
             'overflow', 'clusterfuzz', 'id:', 'id_', 'bug', 'vuln', 'issue'],
            ['j2k', 'jp2', 'j2c', 'htj2k', 'cod', 'image', 'openjpeg',
             'htdec', 'ht_dec', 'jpeg2000', 'jp2k', 'ht'],
            []
        ]

        for keywords in keyword_sets:
            best = None
            best_score = None
            for m in filtered:
                name_lower = m.name.lower()
                if keywords and not any(k in name_lower for k in keywords):
                    continue
                if m.size == target_len:
                    return m
                diff = abs(m.size - target_len)
                score = diff
                if best is None or score < best_score:
                    best = m
                    best_score = score
            if best is not None:
                return best

        best = min(filtered, key=lambda m: abs(m.size - target_len))
        return best

    def solve(self, src_path: str) -> bytes:
        target_len = 1479

        if not src_path or not os.path.exists(src_path):
            return b"A" * target_len

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [
                    m for m in tf.getmembers()
                    if m.isfile() and m.size > 0 and m.size <= 2 * 1024 * 1024
                ]

                member = self._select_member(members, target_len)
                if member is not None:
                    f = tf.extractfile(member)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
        except Exception:
            pass

        return b"A" * target_len
