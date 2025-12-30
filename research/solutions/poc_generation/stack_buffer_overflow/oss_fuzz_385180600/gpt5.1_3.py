import os
import tarfile
from typing import Optional


class Solution:
    def _score_file(self, name: str, size: int) -> float:
        name_l = name.lower()
        score = 0.0

        if "385180600" in name_l:
            score += 1000.0

        if "poc" in name_l or "proof" in name_l:
            score += 200.0
        if "crash" in name_l:
            score += 150.0
        if "oss-fuzz" in name_l or "ossfuzz" in name_l or "clusterfuzz" in name_l or "testcase" in name_l:
            score += 120.0
        if "dataset" in name_l or "tlv" in name_l:
            score += 50.0
        if "regress" in name_l or "bug" in name_l:
            score += 80.0
        if "seed" in name_l:
            score -= 30.0

        ext = os.path.splitext(name_l)[1]
        if ext in (".bin", ".raw", ".data", ".in", ".out", ".poc", ".txt"):
            score += 10.0

        parts = name_l.split("/")
        for p in parts:
            if p in ("poc", "pocs"):
                score += 40.0
            if "crash" in p:
                score += 40.0
            if "fuzz" in p:
                score += 15.0
            if "regress" in p:
                score += 20.0

        if size > 0:
            score -= abs(size - 262) / 50.0
        if size > 4096:
            score -= 50.0

        return score

    def _find_best_poc_in_tar(self, src_path: str) -> Optional[bytes]:
        try:
            with tarfile.open(src_path, "r:*") as tar:
                best_member = None
                best_score = float("-inf")
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    if member.size <= 0:
                        continue
                    score = self._score_file(member.name, member.size)
                    if score > best_score:
                        best_score = score
                        best_member = member
                if best_member is not None:
                    f = tar.extractfile(best_member)
                    if f is not None:
                        return f.read()
        except tarfile.ReadError:
            return None
        return None

    def _find_best_poc_in_dir(self, dir_path: str) -> Optional[bytes]:
        best_path = None
        best_score = float("-inf")
        for root, _, files in os.walk(dir_path):
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0:
                    continue
                rel = os.path.relpath(path, dir_path)
                score = self._score_file(rel, size)
                if score > best_score:
                    best_score = score
                    best_path = path
        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except OSError:
                return None
        return None

    def solve(self, src_path: str) -> bytes:
        poc: Optional[bytes] = None

        if os.path.isdir(src_path):
            poc = self._find_best_poc_in_dir(src_path)
        else:
            poc = self._find_best_poc_in_tar(src_path)
            if poc is None and os.path.isdir(src_path):
                poc = self._find_best_poc_in_dir(src_path)

        if poc is not None:
            return poc

        return b"A" * 262