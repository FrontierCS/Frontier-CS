import os
import tarfile
import tempfile
import subprocess
import time
import random
import shutil
from typing import List, Tuple, Optional


class Solution:
    def _extract_tarball(self, src_path: str, dst_dir: str) -> str:
        with tarfile.open(src_path, "r:*") as tar:
            tar.extractall(dst_dir)
        # Determine project root: if single top-level directory, use it
        entries = [e for e in os.listdir(dst_dir) if not e.startswith(".")]
        if len(entries) == 1:
            sole = os.path.join(dst_dir, entries[0])
            if os.path.isdir(sole):
                return sole
        return dst_dir

    def _gather_sources(self, root: str) -> Tuple[List[str], List[str]]:
        c_files: List[str] = []
        cpp_files: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                lower = name.lower()
                full = os.path.join(dirpath, name)
                if lower.endswith(".c"):
                    c_files.append(full)
                elif lower.endswith((".cc", ".cpp", ".cxx")):
                    cpp_files.append(full)
        return c_files, cpp_files

    def _select_preferred_sources(
        self, root: str, c_files: List[str], cpp_files: List[str]
    ) -> List[str]:
        # Heuristic: prefer files mentioning both main and ndpi_search_setup_capwap / capwap
        main_files: List[str] = []
        capwap_files: List[str] = []
        for paths in (c_files, cpp_files):
            for path in paths:
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read(100_000)
                except OSError:
                    continue
                low = txt.lower()
                has_main = "main(" in low
                has_capwap = "ndpi_search_setup_capwap" in low or "capwap" in low
                if has_main:
                    main_files.append(path)
                if has_capwap:
                    capwap_files.append(path)

        selected: List[str] = []

        if main_files:
            # Prefer main files that also look related to capwap
            ranked = []
            for m in main_files:
                try:
                    with open(m, "r", errors="ignore") as f:
                        txt = f.read(100_000).lower()
                except OSError:
                    txt = ""
                score = 0
                if "ndpi_search_setup_capwap" in txt:
                    score += 2
                if "capwap" in txt:
                    score += 1
                ranked.append((score, len(m), m))
            ranked.sort(reverse=True)
            best_main = ranked[0][2]
            selected.append(best_main)
        # Add all capwap-related files
        for p in capwap_files:
            if p not in selected:
                selected.append(p)

        if selected:
            return selected

        # Fallback: select all fairly small C/C++ files
        small_sources: List[str] = []
        for path in c_files + cpp_files:
            try:
                sz = os.path.getsize(path)
            except OSError:
                continue
            if sz <= 400_000:
                small_sources.append(path)
        if small_sources:
            return small_sources

        # Final fallback: all sources
        return c_files + cpp_files

    def _compile_sources(
        self, root: str, sources: List[str], out_path: str
    ) -> Tuple[bool, bool]:
        if not sources:
            return False, False

        is_cpp = any(
            s.lower().endswith((".cc", ".cpp", ".cxx")) for s in sources
        )

        compiler_order: List[Tuple[str, List[str]]] = []

        if is_cpp:
            compiler_order.extend(
                [
                    ("clang++", ["-fsanitize=address"]),
                    ("g++", ["-fsanitize=address"]),
                    ("clang++", []),
                    ("g++", []),
                ]
            )
        else:
            compiler_order.extend(
                [
                    ("clang", ["-fsanitize=address"]),
                    ("gcc", ["-fsanitize=address"]),
                    ("clang", []),
                    ("gcc", []),
                ]
            )

        for cc, extra in compiler_order:
            if shutil.which(cc) is None:
                continue
            cmd = [cc, "-g", "-O1", "-fno-omit-frame-pointer"] + extra + sources + [
                "-o",
                out_path,
            ]
            try:
                res = subprocess.run(
                    cmd,
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                continue
            if res.returncode == 0 and os.path.isfile(out_path):
                asan_enabled = "-fsanitize=address" in extra
                return True, asan_enabled
        return False, False

    def _fuzz_for_asan_crash(
        self, bin_path: str, max_time: float = 10.0, max_len: int = 64
    ) -> Optional[bytes]:
        start = time.time()
        random.seed(0)
        crash_markers = [
            b"AddressSanitizer",
            b"heap-buffer-overflow",
            b"heap-buffer-overrun",
            b"buffer-overflow",
            b"buffer-overrun",
        ]
        # Try some structured-ish seeds around length 33 as well
        fixed_lengths = [33, 32, 34, 24, 40]

        attempt = 0
        while time.time() - start < max_time:
            # Alternate between fixed and random lengths
            if attempt < len(fixed_lengths):
                length = fixed_lengths[attempt]
            else:
                length = random.randint(1, max_len)
            attempt += 1
            try:
                data = os.urandom(max(1, length))
            except NotImplementedError:
                # Fallback if os.urandom not available
                data = bytes(random.getrandbits(8) for _ in range(max(1, length)))
            try:
                res = subprocess.run(
                    [bin_path],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=2,
                )
            except subprocess.TimeoutExpired:
                continue
            except OSError:
                break

            if res.returncode != 0:
                err = res.stderr or b""
                if any(m in err for m in crash_markers):
                    return data
        return None

    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                proj_root = self._extract_tarball(src_path, tmpdir)
            except Exception:
                # If extraction fails, return simple fallback PoC
                return b"A" * 33

            c_files, cpp_files = self._gather_sources(proj_root)
            if not c_files and not cpp_files:
                return b"A" * 33

            preferred_sources = self._select_preferred_sources(
                proj_root, c_files, cpp_files
            )
            bin_path = os.path.join(proj_root, "poc_bin")

            compiled, asan_enabled = self._compile_sources(
                proj_root, preferred_sources, bin_path
            )

            if not compiled:
                # Fallback: try compiling all sources
                all_sources = c_files + cpp_files
                compiled, asan_enabled = self._compile_sources(
                    proj_root, all_sources, bin_path
                )

            if compiled and asan_enabled:
                poc = self._fuzz_for_asan_crash(bin_path)
                if poc is not None:
                    return poc

        # Final fallback: deterministic 33-byte payload
        return b"A" * 33