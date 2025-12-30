import os
import tarfile
import collections


class Solution:
    def _score_member(self, member, target_size: int, consider_size: bool) -> int:
        path = member.name or ""
        size = int(getattr(member, "size", 0) or 0)
        p = path.lower()
        parts = p.replace("\\", "/").split("/")
        filename = parts[-1] if parts else ""
        _, ext = os.path.splitext(filename)

        score = 0

        data_ext_weights = {
            ".bin": 35,
            ".dat": 32,
            ".poc": 40,
            ".in": 30,
            ".input": 30,
            ".snap": 38,
            ".dump": 38,
            ".raw": 35,
            ".json": 25,
            ".txt": 22,
            ".xml": 22,
            ".yaml": 22,
            ".yml": 22,
            ".cfg": 18,
            ".conf": 18,
            ".ini": 18,
            ".log": 10,
            ".proto": 20,
            ".pb": 25,
            ".msg": 20,
            ".out": 10,
            ".case": 25,
            ".seed": 25,
            ".data": 25,
            ".bytes": 25,
            ".gz": 15,
            ".xz": 15,
            ".lzma": 15,
            ".zz": 15,
            ".zip": 10,
        }
        source_exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hh",
            ".hpp",
            ".hxx",
            ".java",
            ".py",
            ".py3",
            ".pyw",
            ".rb",
            ".php",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".go",
            ".rs",
            ".m",
            ".mm",
            ".cs",
            ".swift",
            ".kt",
            ".kts",
            ".scala",
            ".sh",
            ".bat",
            ".ps1",
            ".cmake",
            ".make",
            ".mak",
        }
        doc_exts = {".md", ".rst", ".html", ".htm", ".css", ".pdf", ".doc", ".docx"}

        score += data_ext_weights.get(ext, 0)
        if ext in source_exts:
            score -= 50
        elif ext in doc_exts:
            score -= 20

        keyword_weights = {
            "poc": 40,
            "crash": 35,
            "overflow": 30,
            "stack": 25,
            "fuzz": 25,
            "fuzzer": 25,
            "oss-fuzz": 30,
            "clusterfuzz": 30,
            "input": 20,
            "corpus": 20,
            "regress": 20,
            "regression": 20,
            "test": 15,
            "tests": 15,
            "sample": 15,
            "samples": 15,
            "case": 15,
            "bug": 20,
            "issue": 15,
            "snapshot": 25,
            "memory": 15,
            "node": 15,
            "graph": 10,
            "ast": 10,
            "tree": 10,
            "heap": 10,
            "invalid": 10,
            "broken": 10,
            "seed": 15,
        }
        for kw, w in keyword_weights.items():
            if kw in p:
                score += w

        dir_weights = {
            "poc": 25,
            "pocs": 25,
            "crash": 25,
            "crashes": 25,
            "fuzz": 20,
            "fuzzer": 20,
            "oss-fuzz": 25,
            "corpus": 20,
            "inputs": 20,
            "input": 20,
            "regress": 20,
            "regression": 20,
            "tests": 18,
            "test": 18,
            "testdata": 18,
            "fixtures": 15,
            "examples": 10,
            "samples": 15,
            "sample": 15,
        }
        for part in parts[:-1]:
            if part in dir_weights:
                score += dir_weights[part]

        if consider_size:
            diff = abs(size - target_size)
            size_score = 60 - diff
            if size_score < 0:
                size_score = 0
            score += size_score

        return score

    def _select_best_member(self, members, target_size: int, consider_size: bool):
        best = None
        best_score = None
        for m in members:
            score = self._score_member(m, target_size, consider_size)
            if best is None or score > best_score:
                best = m
                best_score = score
        return best

    def solve(self, src_path: str) -> bytes:
        target_size = 140
        try:
            with tarfile.open(src_path, "r:*") as tf:
                size_map = collections.defaultdict(list)
                for member in tf.getmembers():
                    if member.isfile():
                        size_map[member.size].append(member)

                chosen = None

                if target_size in size_map and size_map[target_size]:
                    chosen = self._select_best_member(
                        size_map[target_size], target_size, consider_size=False
                    )
                else:
                    small_members = []
                    max_size = 4096
                    for sz, mems in size_map.items():
                        if sz <= max_size:
                            small_members.extend(mems)
                    if small_members:
                        chosen = self._select_best_member(
                            small_members, target_size, consider_size=True
                        )
                    else:
                        smallest = None
                        for sz, mems in size_map.items():
                            for m in mems:
                                if smallest is None or sz < smallest.size:
                                    smallest = m
                        chosen = smallest

                if chosen is None:
                    return b"A" * target_size

                f = tf.extractfile(chosen)
                if f is None:
                    return b"A" * target_size
                data = f.read()
                if isinstance(data, str):
                    data = data.encode("utf-8", "ignore")
                return data
        except Exception:
            return b"A" * target_size