import os
import tarfile
import zipfile
import tempfile
import subprocess
import random
import string
import shutil
from pathlib import Path
from typing import Optional, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        src = Path(src_path)
        if src.is_dir():
            return self._solve_in_directory(src)
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                dest = Path(tmpdir)
                self._extract_archive(src, dest)
                project_root = self._find_project_root(dest)
                return self._solve_in_directory(project_root)

    def _extract_archive(self, archive_path: Path, dest: Path) -> None:
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(dest)
        elif zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest)
        else:
            # Not an archive or unknown format; nothing to extract.
            pass

    def _find_project_root(self, dest: Path) -> Path:
        try:
            entries = [p for p in dest.iterdir() if not p.name.startswith('.')]
        except FileNotFoundError:
            return dest
        if len(entries) == 1 and entries[0].is_dir():
            return entries[0]
        return dest

    def _solve_in_directory(self, project_root: Path) -> bytes:
        fast_float_include_root = self._find_fast_float_include_root(project_root)
        if fast_float_include_root is not None:
            poc = self._generate_poc_fast_float(project_root, fast_float_include_root)
            if poc is not None:
                return poc
        # Fallback generic PoC, 16 bytes long, mimicking minus + non-infinity text.
        fallback = b"-not_infinity!!\n"
        return fallback[:16]

    def _find_fast_float_include_root(self, project_root: Path) -> Optional[Path]:
        try:
            for path in project_root.rglob("fast_float.h"):
                if path.is_file():
                    parent = path.parent
                    if parent.name == "fast_float":
                        return parent.parent
                    else:
                        return parent
        except Exception:
            pass
        return None

    def _generate_poc_fast_float(self, project_root: Path, include_root: Path) -> Optional[bytes]:
        random.seed(0)
        harness_src = r'''
#include <iostream>
#include <string>
#include "fast_float/fast_float.h"

int main() {
    std::string input;
    std::getline(std::cin, input, '\0');
    if (input.empty()) {
        return 0;
    }
    double value = 0.0;
    auto result = fast_float::from_chars(input.data(), input.data() + input.size(), value);
    (void)result;
    return 0;
}
'''
        harness_file = project_root / "ff_poc_harness.cpp"
        try:
            with open(harness_file, "w") as f:
                f.write(harness_src)
        except Exception:
            return None

        bin_path = project_root / "ff_poc_harness_bin"
        compilers = ["clang++", "g++"]
        compiled = False
        for use_sanitize in (True, False):
            if compiled:
                break
            for compiler in compilers:
                if self._compile_fast_float_harness(
                    compiler,
                    harness_file,
                    include_root,
                    bin_path,
                    use_sanitize,
                    project_root,
                ):
                    compiled = True
                    break
        if not compiled or not bin_path.is_file():
            return None

        candidates = self._candidate_strings_fast_float()
        for s in candidates:
            if self._run_harness_crashes(bin_path, s):
                reduced = self._reduce_crashing_input(bin_path, s)
                return reduced.encode("latin1", "ignore")

        max_random = 2000
        for s in self._random_strings_fast_float(max_random):
            if self._run_harness_crashes(bin_path, s):
                reduced = self._reduce_crashing_input(bin_path, s)
                return reduced.encode("latin1", "ignore")

        return None

    def _compile_fast_float_harness(
        self,
        compiler: str,
        harness_file: Path,
        include_root: Path,
        bin_path: Path,
        use_sanitize: bool,
        cwd: Path,
    ) -> bool:
        if shutil.which(compiler) is None:
            return False
        cmd = [compiler, "-std=c++17", "-O1", "-g"]
        if use_sanitize:
            cmd.extend(["-fsanitize=address,undefined", "-fno-omit-frame-pointer"])
        cmd.extend([str(harness_file), "-I", str(include_root), "-o", str(bin_path)])
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(cwd),
                timeout=120,
            )
        except Exception:
            return False
        return res.returncode == 0

    def _run_harness_crashes(self, bin_path: Path, s: str) -> bool:
        try:
            res = subprocess.run(
                [str(bin_path)],
                input=s.encode("latin1", "ignore"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=0.05,
            )
        except subprocess.TimeoutExpired:
            return False
        return res.returncode != 0

    def _candidate_strings_fast_float(self) -> List[str]:
        base_infs = ["inf", "infinity", "Inf", "Infinity", "INF", "INFINITY"]
        base_nans = ["nan", "NaN", "NAN"]
        mutate_chars = "0123456789+-xyzXYZ"
        appended = "0123456789+-xX.iIfFnNyY"
        seeds = set()

        for b in base_infs:
            seeds.add("-" + b)
            for i in range(len(b)):
                for rep in mutate_chars:
                    if rep != b[i]:
                        mutated = b[:i] + rep + b[i + 1 :]
                        seeds.add("-" + mutated)
            for ext in appended:
                seeds.add("-" + b + ext)

        for b in base_nans:
            seeds.add("-" + b)
            for i in range(len(b)):
                for rep in mutate_chars:
                    if rep != b[i]:
                        mutated = b[:i] + rep + b[i + 1 :]
                        seeds.add("-" + mutated)
            for ext in appended:
                seeds.add("-" + b + ext)

        extra = set()
        for s in seeds:
            extra.add(s + " ")
            extra.add(" " + s)
        seeds.update(extra)

        seq = [s for s in seeds if 1 < len(s) <= 32]
        random.shuffle(seq)
        if len(seq) > 2000:
            seq = seq[:2000]
        return seq

    def _random_strings_fast_float(self, count: int):
        letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        digits = "0123456789"
        specials = "+-_. xX"
        infnan = "infINFnanyNAN"
        allchars = letters + digits + specials + infnan
        for _ in range(count):
            length = random.randint(2, 32)
            chars = ["-"]
            for _i in range(1, length):
                r = random.random()
                if r < 0.5:
                    chars.append(random.choice(infnan))
                elif r < 0.8:
                    chars.append(random.choice(digits))
                else:
                    chars.append(random.choice(allchars))
            yield "".join(chars)

    def _reduce_crashing_input(self, bin_path: Path, s: str) -> str:
        current = s
        changed = True
        while changed and len(current) > 1:
            changed = False
            for i in range(len(current)):
                if len(current) <= 1:
                    break
                candidate = current[:i] + current[i + 1 :]
                if not candidate:
                    continue
                if self._run_harness_crashes(bin_path, candidate):
                    current = candidate
                    changed = True
                    break
        return current