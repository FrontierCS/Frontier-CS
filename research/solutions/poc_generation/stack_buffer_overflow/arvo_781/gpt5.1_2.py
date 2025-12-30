import os
import tarfile
import tempfile
import subprocess
import stat
import random
import string
import shutil
import time


class Solution:
    def solve(self, src_path: str) -> bytes:
        random.seed(time.time())
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            self._extract_tarball(src_path, tmpdir)
            root = self._detect_project_root(tmpdir)
            executables = self._build_and_find_executables(root)
            for exe in executables:
                poc = self._find_poc_for_exe(exe)
                if poc is not None:
                    return poc
        except Exception:
            pass
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
        return b"A" * 8

    @staticmethod
    def _extract_tarball(src_path: str, dst_dir: str) -> None:
        with tarfile.open(src_path, "r:*") as tar:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory

            def safe_extract(tar_obj, path=".", members=None):
                for member in tar_obj.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        continue
                tar_obj.extractall(path, members)

            safe_extract(tar, dst_dir)

    @staticmethod
    def _detect_project_root(tmpdir: str) -> str:
        entries = [e for e in os.listdir(tmpdir) if not e.startswith(".")]
        if len(entries) == 1:
            single = os.path.join(tmpdir, entries[0])
            if os.path.isdir(single):
                return single
        return tmpdir

    def _build_and_find_executables(self, root: str):
        build_sh = None
        for dirpath, _, filenames in os.walk(root):
            if "build.sh" in filenames:
                build_sh = os.path.join(dirpath, "build.sh")
                break

        if build_sh is not None:
            try:
                st = os.stat(build_sh)
                os.chmod(build_sh, st.st_mode | stat.S_IXUSR)
            except Exception:
                pass
            try:
                subprocess.run(
                    ["bash", build_sh],
                    cwd=os.path.dirname(build_sh),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=180,
                    check=False,
                )
            except Exception:
                pass
        else:
            # Fallback generic build attempts
            try:
                if os.path.exists(os.path.join(root, "configure")):
                    subprocess.run(
                        ["sh", "configure"],
                        cwd=root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                        check=False,
                    )
                    subprocess.run(
                        ["make", "-j4"],
                        cwd=root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=300,
                        check=False,
                    )
                elif os.path.exists(os.path.join(root, "CMakeLists.txt")):
                    build_dir = os.path.join(root, "build")
                    os.makedirs(build_dir, exist_ok=True)
                    subprocess.run(
                        ["cmake", ".."],
                        cwd=build_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                        check=False,
                    )
                    subprocess.run(
                        ["make", "-j4"],
                        cwd=build_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=300,
                        check=False,
                    )
                else:
                    subprocess.run(
                        ["make", "-j4"],
                        cwd=root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=300,
                        check=False,
                    )
            except Exception:
                pass

        executables = []
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    if not os.path.isfile(path):
                        continue
                    st = os.stat(path)
                    if not (st.st_mode & stat.S_IXUSR):
                        continue
                    with open(path, "rb") as f:
                        magic = f.read(4)
                    if magic != b"\x7fELF":
                        continue
                    executables.append(path)
                except Exception:
                    continue

        executables.sort(key=lambda p: os.path.getsize(p), reverse=True)
        return executables

    def _find_poc_for_exe(self, exe_path: str):
        # Stage 1: deterministic patterns
        static_patterns = self._generate_static_patterns()
        max_total_runs = 700
        runs = 0

        for pat in static_patterns:
            if runs >= max_total_runs:
                return None
            variants = self._generate_input_variants_from_pattern(pat)
            for data in variants:
                if runs >= max_total_runs:
                    return None
                runs += 1
                if self._run_and_is_crash(exe_path, data):
                    return data

        # Stage 2: random fuzzing with regex-like patterns
        max_random = max_total_runs - runs
        for _ in range(max_random):
            pattern = self._generate_random_regex_pattern()
            data = self._generate_random_input_from_pattern(pattern)
            if self._run_and_is_crash(exe_path, data):
                return data

        return None

    @staticmethod
    def _run_and_is_crash(exe_path: str, data: bytes) -> bool:
        try:
            res = subprocess.run(
                [exe_path],
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=1.0,
            )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        rc = res.returncode
        if rc == 0:
            return False

        # Treat signal-terminated processes as crashes
        if rc < 0 or rc >= 128:
            return True

        err = res.stderr or b""
        crash_keywords = [
            b"AddressSanitizer",
            b"stack-buffer-overflow",
            b"stack overflow",
            b"buffer-overflow",
            b"SIGSEGV",
            b"segmentation fault",
            b"stack smashing detected",
            b"runtime error",
        ]
        for kw in crash_keywords:
            if kw in err:
                return True
        return False

    @staticmethod
    def _generate_static_patterns():
        patterns = set()

        # Basic literals and simple quantifiers
        base_lits = ["a", "b", "ab", "abc"]
        quants = ["", "?", "+", "*"]
        for lit in base_lits:
            patterns.add(lit)
            for q in quants:
                patterns.add(lit + q)

        patterns.update(
            [
                ".",
                ".*",
                "^a$",
                "^.*$",
                "a?b",
                "ab+c",
                "a*b*c*d*",
                "(?:a)",
                "(?:a|b)",
                "(?:a*)+",
                "(?:(a)b)+",
            ]
        )

        # Single and nested capturing groups
        for lit in base_lits:
            for q1 in quants:
                for q2 in quants:
                    patterns.add(f"({lit}{q1}){q2}")
                    patterns.add(f"(({lit}{q1})){q2}")

        # Two-group combinations
        for lit1 in ["a", "ab"]:
            for lit2 in ["b", "bc"]:
                patterns.add(f"({lit1})({lit2})")
                patterns.add(f"({lit1})({lit2})+")
                patterns.add(f"({lit1}{lit2})|({lit2}{lit1})")
                patterns.add(f"({lit1})+({lit2})*")

        # Some patterns with alternations and nesting
        patterns.update(
            [
                "(a|b)",
                "(a|b)*",
                "(a|b)+",
                "((a))",
                "((a)*)",
                "(ab)",
                "^(a*)$",
                "^(a+)$",
                "((ab)+)+",
                "(a(b)c)",
                "a(b(c)d)e",
                "((a|))+",  # odd but legal
                "(a*)*b",
                "((a|b)*)+",
                "(a|aa)+$",
                "(ab|a)*",
                "(a?)+",
                "((ab)?)+",
                "((a)+)+b",
                "(a(b(c(d(e)f)g)h)i)j",
                "((((a))))",
                "(a{1,3})",
                "((a{0,2})b)+",
            ]
        )

        # Backreference-heavy patterns
        patterns.update(
            [
                r"(a)\1",
                r"(a)(b)\2",
                r"(a|b)\1",
                r"(.+)\1",
                r"(\w+)\1",
                r"([0-9]+)\1",
                r"((a*)b)+",
                r"((ab)*c)+",
            ]
        )

        # Limit the total number to keep runtime bounded
        # Deterministic order
        patterns_list = sorted(patterns)
        if len(patterns_list) > 200:
            patterns_list = patterns_list[:200]
        return patterns_list

    @staticmethod
    def _generate_input_variants_from_pattern(pattern: str):
        bs = pattern.encode("ascii", "ignore") or b"a"
        variants = []

        # Pattern only
        variants.append(bs)

        # Pattern + newline + small subject
        variants.append(bs + b"\n" + b"abc")

        # Pattern + null + small subject
        variants.append(bs + b"\x00" + b"abc")

        # First byte as pattern length
        if len(bs) <= 250:
            L = len(bs)
            variants.append(bytes([L]) + bs)
            variants.append(bytes([L]) + bs + b"abc")

        # 2-byte length (LE and BE)
        if len(bs) <= 65535:
            L2_le = len(bs).to_bytes(2, "little")
            L2_be = len(bs).to_bytes(2, "big")
            variants.append(L2_le + bs)
            variants.append(L2_le + bs + b"abc")
            variants.append(L2_be + bs)
            variants.append(L2_be + bs + b"abc")

        # 4-byte LE length
        L4_le = len(bs).to_bytes(4, "little")
        variants.append(L4_le + bs)
        variants.append(L4_le + bs + b"abc")

        # Prefix with a zero options byte
        variants.append(b"\x00" + bs)
        variants.append(b"\x00" + bs + b"abc")

        # Deduplicate while preserving order
        out = []
        seen = set()
        for v in variants:
            if v not in seen:
                seen.add(v)
                out.append(v)
        return out

    @staticmethod
    def _generate_random_regex_pattern() -> str:
        base_chars = "ab"
        quantifiers = ["", "?", "+", "*"]
        s = ""
        n_groups = random.randint(0, 3)
        for _ in range(n_groups):
            if random.random() < 0.6 or not s:
                s += random.choice(base_chars) * random.randint(1, 3)
            # Choose capturing vs non-capturing
            if random.random() < 0.7:
                s += "("
            else:
                s += "(?:"
            inner_len = random.randint(1, 4)
            inner = "".join(random.choice(base_chars) for _ in range(inner_len))
            s += inner + ")"
            s += random.choice(quantifiers)
            if random.random() < 0.3:
                s += "|"
        s += random.choice(base_chars) * random.randint(1, 3)
        if not s:
            s = "a"
        if len(s) > 32:
            s = s[:32]
        return s

    @staticmethod
    def _generate_random_input_from_pattern(pattern: str) -> bytes:
        bs = pattern.encode("ascii", "ignore") or b"a"
        subj_len = random.randint(1, 8)
        subj = "".join(random.choice("abc") for _ in range(subj_len)).encode("ascii")
        form = random.randint(0, 4)

        if form == 0:
            return bs
        elif form == 1:
            return bs + b"\n" + subj
        elif form == 2:
            if len(bs) <= 250:
                return bytes([len(bs)]) + bs + subj
            return bs + subj
        elif form == 3:
            if len(bs) <= 65535:
                return len(bs).to_bytes(2, "little") + bs + subj
            return bs + subj
        else:
            return bs + b"\x00" + subj