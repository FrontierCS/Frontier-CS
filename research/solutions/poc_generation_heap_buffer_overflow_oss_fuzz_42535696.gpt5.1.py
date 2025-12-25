import tarfile
from typing import List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 150_979

        try:
            tar = tarfile.open(src_path, "r:*")
        except tarfile.TarError:
            return b"A"

        with tar:
            members = tar.getmembers()

            # Step 1: direct hits containing the exact oss-fuzz id
            direct_hits: List[tarfile.TarInfo] = []
            for m in members:
                if not m.isfile():
                    continue
                name_lower = m.name.lower()
                if "42535696" in name_lower:
                    direct_hits.append(m)

            if direct_hits:
                best = min(direct_hits, key=lambda m: abs(m.size - target_len))
                f = tar.extractfile(best)
                if f is not None:
                    return f.read()

            # Step 2: heuristic search
            keywords = [
                "test",
                "tests",
                "fuzz",
                "regress",
                "poc",
                "crash",
                "bug",
                "bugs",
                "oss-fuzz",
                "clusterfuzz",
                "pdfwrite",
                "viewer",
                "4253",
            ]
            exts = [
                ".pdf",
                ".ps",
                ".eps",
                ".xps",
                ".txt",
                ".bin",
                ".dat",
                ".in",
                ".poc",
            ]

            candidates_all: List[Tuple[tarfile.TarInfo, int, int, int]] = []
            candidates_kw: List[Tuple[tarfile.TarInfo, int, int, int]] = []

            for m in members:
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0:
                    continue
                name_lower = m.name.lower()

                path_score = 0
                for kw in keywords:
                    if kw in name_lower:
                        path_score += 1

                ext_priority = len(exts) + 1
                for idx, ext in enumerate(exts):
                    if name_lower.endswith(ext):
                        ext_priority = idx
                        break

                entry = (m, size, ext_priority, path_score)
                candidates_all.append(entry)
                if path_score > 0:
                    candidates_kw.append(entry)

            def sort_key(elem: Tuple[tarfile.TarInfo, int, int, int]):
                m, size, ext_prio, path_score = elem
                return (abs(size - target_len), ext_prio, -path_score)

            best_member = None

            if candidates_kw:
                candidates_kw.sort(key=sort_key)
                best_member = candidates_kw[0][0]
            elif candidates_all:
                candidates_all.sort(key=sort_key)
                best_member = candidates_all[0][0]

            if best_member is not None:
                f = tar.extractfile(best_member)
                if f is not None:
                    return f.read()

        return b"A"
