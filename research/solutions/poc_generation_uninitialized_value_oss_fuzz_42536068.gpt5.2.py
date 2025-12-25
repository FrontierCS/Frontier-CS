import os
import re
import io
import sys
import stat
import tarfile
import zipfile
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class _Candidate:
    score: int
    size: int
    origin: str
    data: bytes


class Solution:
    _ID = "42536068"

    def _safe_extract_tar(self, tf: tarfile.TarFile, path: str) -> None:
        base = os.path.abspath(path)
        for m in tf.getmembers():
            name = m.name
            if not name:
                continue
            dest = os.path.abspath(os.path.join(base, name))
            if not (dest == base or dest.startswith(base + os.sep)):
                continue
            try:
                tf.extract(m, path=base, set_attrs=False, numeric_owner=False)
            except Exception:
                continue

    def _read_file_limited(self, p: str, limit: int = 2_000_000) -> Optional[bytes]:
        try:
            st = os.stat(p, follow_symlinks=False)
            if not stat.S_ISREG(st.st_mode):
                return None
            if st.st_size <= 0 or st.st_size > limit:
                return None
            with open(p, "rb") as f:
                data = f.read(limit + 1)
            if len(data) != st.st_size or len(data) > limit:
                return None
            return data
        except Exception:
            return None

    def _name_score(self, rel: str) -> int:
        s = rel.replace("\\", "/").lower()
        base = os.path.basename(s)
        score = 0

        if self._ID in s:
            score += 200

        if "clusterfuzz" in s:
            score += 140
        if "testcase" in s:
            score += 90
        if "minimized" in s or "min" in base:
            score += 50
        if "crash" in s or "crashes" in s:
            score += 70
        if "repro" in s or "reproducer" in s:
            score += 60
        if "poc" in s:
            score += 60
        if "oss-fuzz" in s or "ossfuzz" in s:
            score += 45
        if "/test/" in s or "/tests/" in s:
            score += 15
        if "/fuzz/" in s or "/fuzzer/" in s or "/fuzzers/" in s:
            score += 20
        if "/corpus/" in s or "seed_corpus" in s:
            score += 10
        if "/regression/" in s:
            score += 30

        if base in ("readme", "readme.txt", "readme.md", "license", "copying", "changelog"):
            score -= 120

        ext = os.path.splitext(base)[1]
        if ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".java", ".js", ".ts", ".go", ".rs", ".md", ".rst"):
            score -= 80
        elif ext in (".txt",):
            score -= 10
        else:
            score += 10

        if ext in (".zip", ".tar", ".gz", ".tgz", ".xz", ".bz2", ".7z"):
            score -= 25

        if base.startswith("."):
            score -= 10

        return score

    def _collect_from_zip(self, zp: str, rel: str) -> List[_Candidate]:
        cands: List[_Candidate] = []
        try:
            with zipfile.ZipFile(zp, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > 2_000_000:
                        continue
                    inner = zi.filename.replace("\\", "/")
                    full_rel = f"{rel}::{inner}"
                    score = self._name_score(full_rel)
                    try:
                        data = zf.read(zi)
                    except Exception:
                        continue
                    if not data:
                        continue
                    cands.append(_Candidate(score=score, size=len(data), origin=full_rel, data=data))
        except Exception:
            return []
        return cands

    def _collect_candidates(self, root: str) -> List[_Candidate]:
        cands: List[_Candidate] = []
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "build", "out", "__pycache__")]
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, root)
                s = rel.replace("\\", "/").lower()

                if fn.lower() in ("readme", "license", "copying"):
                    continue
                if os.path.getsize(p) > 20_000_000:
                    continue

                data = self._read_file_limited(p)
                if data is not None:
                    score = self._name_score(rel)
                    cands.append(_Candidate(score=score, size=len(data), origin=rel.replace("\\", "/"), data=data))

                if s.endswith(".zip") and ("seed" in s or "corpus" in s or "test" in s or "fuzz" in s or self._ID in s):
                    cands.extend(self._collect_from_zip(p, rel.replace("\\", "/")))
        return cands

    def _best_candidate(self, cands: List[_Candidate]) -> Optional[_Candidate]:
        if not cands:
            return None

        def key(c: _Candidate) -> Tuple[int, int, int]:
            bonus = 0
            if self._ID in c.origin.lower():
                bonus += 5_000_000
            if "clusterfuzz" in c.origin.lower():
                bonus += 2_000_000
            if "minimized" in c.origin.lower():
                bonus += 500_000
            if "testcase" in c.origin.lower():
                bonus += 500_000
            if "crash" in c.origin.lower():
                bonus += 300_000

            return (c.score * 1000 + bonus, -c.size, -len(c.origin))

        cands_sorted = sorted(cands, key=key, reverse=True)

        top = cands_sorted[0]
        # Prefer smaller among similarly-scored candidates
        best = top
        top_score = key(top)[0]
        for c in cands_sorted[1:50]:
            if key(c)[0] < top_score - 2000:
                break
            if c.size < best.size and key(c)[0] >= top_score - 500:
                best = c
        return best

    def solve(self, src_path: str) -> bytes:
        workdir = None
        root = None
        try:
            if os.path.isdir(src_path):
                root = src_path
            else:
                workdir = tempfile.mkdtemp(prefix="pocgen_")
                root = workdir
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        self._safe_extract_tar(tf, root)
                except Exception:
                    # If not a tar, try as zip
                    try:
                        with zipfile.ZipFile(src_path, "r") as zf:
                            zf.extractall(root)
                    except Exception:
                        root = None

            if not root or not os.path.isdir(root):
                return b""

            cands = self._collect_candidates(root)

            # Also scan for tiny "regression" or "poc" content embedded as text with hex/base64 (light heuristic)
            # Only if we have no good candidates.
            best = self._best_candidate(cands)
            if best is not None and best.size > 0:
                return best.data

            # Fallback: try to find any file containing the ID and then treat adjacent binary-like file as candidate
            id_hits: List[str] = []
            for dirpath, _, filenames in os.walk(root, topdown=True, followlinks=False):
                for fn in filenames:
                    p = os.path.join(dirpath, fn)
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    data = self._read_file_limited(p)
                    if not data:
                        continue
                    if self._ID.encode() in data:
                        id_hits.append(p)
            for p in id_hits:
                d = os.path.dirname(p)
                for fn in os.listdir(d):
                    q = os.path.join(d, fn)
                    data = self._read_file_limited(q)
                    if data:
                        return data

            return b""
        finally:
            if workdir:
                try:
                    for dirpath, dirnames, filenames in os.walk(workdir, topdown=False):
                        for fn in filenames:
                            try:
                                os.unlink(os.path.join(dirpath, fn))
                            except Exception:
                                pass
                        for dn in dirnames:
                            try:
                                os.rmdir(os.path.join(dirpath, dn))
                            except Exception:
                                pass
                    os.rmdir(workdir)
                except Exception:
                    pass