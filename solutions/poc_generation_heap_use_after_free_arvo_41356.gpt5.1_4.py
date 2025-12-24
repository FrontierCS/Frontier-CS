import os
import tarfile
import tempfile
import subprocess


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    tar.extractall(tmpdir)
            except Exception:
                return self._static_default_poc()

            poc = None
            try:
                binary_path, uses_asan = self._compile_program(tmpdir)
            except Exception:
                binary_path, uses_asan = None, False

            if binary_path is not None:
                try:
                    poc = self._find_poc_with_binary(binary_path, uses_asan)
                except Exception:
                    poc = None

            if poc is None:
                poc = self._static_default_poc()

            return poc

    def _compile_program(self, src_root):
        exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".c++",
            ".cp",
            ".c++",
        }
        sources = []
        for root, dirs, files in os.walk(src_root):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    sources.append(os.path.join(root, f))
        if not sources:
            return None, False

        binary = os.path.join(src_root, "poc_target")

        # Try compiling with ASan first, then without if that fails
        for use_asan in (True, False):
            cmd = [
                "g++",
                "-std=c++17",
                "-O0",
                "-g",
                "-fno-omit-frame-pointer",
                "-pthread",
            ]
            if use_asan:
                cmd.append("-fsanitize=address")
            cmd += sources + ["-o", binary]
            try:
                res = subprocess.run(
                    cmd,
                    cwd=src_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
            if res.returncode == 0:
                return binary, use_asan

        return None, False

    def _generate_candidates(self):
        seeds = []

        def add(s):
            if isinstance(s, str):
                s = s.encode("ascii", errors="ignore")
            if not s:
                return
            seeds.append(s)

        # Integer duplicate patterns
        base_ints = ["1", "0", "-1", "2", "42", "2147483647", "-2147483648"]
        for v in base_ints:
            add(f"{v}\n{v}\n")
            add(f"2\n{v}\n{v}\n")

        add("1\n1\n1\n")
        add("3\n1\n2\n2\n")
        add("10\n" + "1\n" * 10)
        add("20\n" + "1\n" * 20)
        add("1 1\n")
        add("0 0\n")
        add("-1 -1\n")
        add("1 1 1 1 1 1 1 1 1 1\n")
        add("5\n1\n2\n3\n4\n4\n")  # includes duplicate 4

        # String duplicate patterns
        for w in ["a", "A", "abc", "node", "data", "value", "key", "duplicate", "test"]:
            add(f"{w}\n{w}\n")

        # Command-like patterns involving "add" semantics
        verbs = ["add", "insert", "push", "append", "put", "set", "ADD", "INSERT", "PUSH"]
        vals = ["1", "0", "-1", "42", "a"]
        for verb in verbs:
            for val in vals:
                add(f"{verb} {val}\n{verb} {val}\n")

        # More structured patterns
        add("10\n" + " ".join(["1"] * 10) + "\n")
        add("5\n1 1 1 1 1\n")
        add("init 1\nadd 1\nadd 1\n")
        add("create 1\ninsert 1\ninsert 1\n")
        add("new 1\nadd 1\nadd 1\n")

        # Deduplicate and sort by length
        unique = []
        seen = set()
        for s in seeds:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        unique.sort(key=len)
        return unique

    def _find_poc_with_binary(self, binary_path, uses_asan):
        candidates = self._generate_candidates()
        for data in candidates:
            try:
                res = subprocess.run(
                    [binary_path],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=0.5,
                )
            except subprocess.TimeoutExpired:
                # Skip hangs
                continue

            rc = res.returncode
            stderr = res.stderr
            low = stderr.lower()

            if uses_asan:
                if (
                    rc != 0
                    and b"addresssanitizer" in low
                    and (
                        b"use-after-free" in low
                        or b"double-free" in low
                        or b"double free" in low
                    )
                ):
                    return data
            else:
                if rc != 0 and (
                    b"free()" in low
                    or b"double free" in low
                    or b"use-after-free" in low
                    or b"segmentation fault" in low
                ):
                    return data

        return None

    def _static_default_poc(self) -> bytes:
        # Fallback PoC: simple numeric input with many duplicate values
        payload = "28\n" + "1\n" * 28
        return payload.encode("ascii")
