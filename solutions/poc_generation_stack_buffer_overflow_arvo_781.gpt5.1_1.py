import os
import tarfile
import tempfile
import subprocess
import time
import random
import shutil
import stat


class Solution:
    def __init__(self):
        self.PER_RUN_TIMEOUT = 0.2
        self.FUZZ_TIME_BUDGET = 12.0
        self.BUILD_TIMEOUT = 40.0

    def solve(self, src_path: str) -> bytes:
        root_dir = None
        temp_dir = None
        try:
            root_dir, temp_dir = self._prepare_source(src_path)
            # Try to find existing binary; if none, attempt to build
            bin_path = self._find_candidate_binary(root_dir)
            if bin_path is None:
                self._build_if_needed(root_dir)
                bin_path = self._find_candidate_binary(root_dir)

            if not bin_path:
                return b"A" * 8

            poc = self._find_poc(bin_path)
            if poc is None:
                return b"A" * 8
            return poc
        except Exception:
            return b"A" * 8
        finally:
            if temp_dir is not None:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _prepare_source(self, src_path):
        # If src_path is a directory, use it directly
        if os.path.isdir(src_path):
            root = src_path
            # Normalize single top-level directory
            entries = [e for e in os.listdir(root) if not e.startswith(".")]
            if len(entries) == 1:
                single = os.path.join(root, entries[0])
                if os.path.isdir(single):
                    root = single
            return root, None

        # If it's a tarball, extract to temp directory
        temp_dir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tar:
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

                    for member in tar.getmembers():
                        member_path = os.path.join(temp_dir, member.name)
                        if not is_within_directory(temp_dir, member_path):
                            continue
                    tar.extractall(temp_dir)
            else:
                # Not a tar file; fall back to parent directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                parent = os.path.dirname(src_path) or "."
                return parent, None
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            parent = os.path.dirname(src_path) or "."
            return parent, None

        root = temp_dir
        # Strip single top-level directory if present
        entries = [e for e in os.listdir(root) if not e.startswith(".")]
        if len(entries) == 1:
            single = os.path.join(root, entries[0])
            if os.path.isdir(single):
                root = single
        return root, temp_dir

    def _is_elf_binary(self, path):
        try:
            st = os.stat(path)
            if not stat.S_ISREG(st.st_mode):
                return False
            if not (st.st_mode & stat.S_IXUSR):
                return False
            with open(path, "rb") as f:
                magic = f.read(4)
            return magic == b"\x7fELF"
        except Exception:
            return False

    def _list_elf_binaries(self, root_dir):
        binaries = []
        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                # Skip obvious scripts and libraries by extension
                base, ext = os.path.splitext(fname)
                if ext in (".sh", ".py", ".pl", ".rb", ".php", ".jar",
                           ".class", ".so", ".a", ".dll", ".txt"):
                    continue
                if self._is_elf_binary(path):
                    binaries.append(path)
        return binaries

    def _choose_best_binary(self, binaries):
        if not binaries:
            return None
        preferred_names = {
            "vuln", "vulnerable", "poc", "test", "target",
            "app", "prog", "main", "a.out"
        }
        best = None
        best_score = None
        for path in binaries:
            name = os.path.basename(path)
            depth = path.count(os.sep)
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            score = depth * 10 + (size / 1024.0)
            if name in preferred_names:
                score -= 50
            if best is None or score < best_score:
                best = path
                best_score = score
        return best

    def _find_candidate_binary(self, root_dir):
        binaries = self._list_elf_binaries(root_dir)
        return self._choose_best_binary(binaries)

    def _build_if_needed(self, root_dir):
        # If there is already a binary, don't build
        if self._find_candidate_binary(root_dir) is not None:
            return

        # Try build.sh scripts
        build_scripts = []
        for dirpath, _, filenames in os.walk(root_dir):
            if "build.sh" in filenames:
                build_scripts.append(os.path.join(dirpath, "build.sh"))

        build_scripts.sort(key=lambda p: p.count(os.sep))
        for script in build_scripts:
            try:
                subprocess.run(
                    ["bash", script],
                    cwd=os.path.dirname(script),
                    timeout=self.BUILD_TIMEOUT,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
            if self._find_candidate_binary(root_dir) is not None:
                return

        # Try Makefile-based builds
        make_dirs = []
        for dirpath, _, filenames in os.walk(root_dir):
            if "Makefile" in filenames or "makefile" in filenames:
                make_dirs.append(dirpath)

        make_dirs.sort(key=lambda p: p.count(os.sep))
        for mdir in make_dirs:
            try:
                subprocess.run(
                    ["make", "-j4"],
                    cwd=mdir,
                    timeout=self.BUILD_TIMEOUT,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
            if self._find_candidate_binary(root_dir) is not None:
                return

    def _run_and_check_crash(self, binary_path, data):
        try:
            proc = subprocess.run(
                [binary_path],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.PER_RUN_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        output = proc.stdout + proc.stderr
        lower = output.lower()

        # Look for sanitizer reports
        if b"addresssanitizer" in lower or b"undefinedbehaviorsanitizer" in lower:
            return True
        if b"sanitizer" in lower and b"error:" in lower:
            return True
        if b"stack-buffer-overflow" in lower or b"heap-buffer-overflow" in lower:
            return True

        # Fallback: generic crash heuristics (segfault, abort)
        if proc.returncode != 0:
            if b"segmentation fault" in lower or b"segfault" in lower:
                return True
            if b"abort" in lower and b"core dumped" in lower:
                return True

        return False

    def _generate_candidate_inputs(self):
        base_patterns = [
            "()",
            "(())",
            "()()",
            "()()()",
            "()()()()",
            "(a)",
            "(a)(b)",
            "((a))",
            "(a)*",
            "(a)+",
            "(a)?",
            "(a|b)",
            "(a)\\1",
            "(a)(b)\\1\\2",
            "((a)(b))",
        ]
        inputs = []

        for pat in base_patterns:
            b = pat.encode("ascii", errors="ignore")
            # Pattern only
            inputs.append(b)
            # Pattern with trailing newline
            inputs.append(b + b"\n")
            # Pattern + newline + simple subject
            inputs.append(b + b"\n" + b"a")
        # Some very small generic inputs
        inputs.append(b"()()()()")
        inputs.append(b"()\n")
        inputs.append(b"(a)\n")
        inputs.append(b"(a)\nAAAA")
        return inputs

    def _random_input(self):
        # Random regex-like pattern with optional subject
        pat_len = random.randint(1, 12)
        pat_chars = "()*+?[]{}^$|.\\abcde12345\n"
        pat = "".join(random.choice(pat_chars) for _ in range(pat_len))

        mode = random.random()
        if mode < 0.34:
            return pat.encode("ascii", errors="ignore")
        elif mode < 0.67:
            return (pat + "\n").encode("ascii", errors="ignore")
        else:
            sub_len = random.randint(0, 8)
            sub_chars = "abcde12345\n"
            sub = "".join(random.choice(sub_chars) for _ in range(sub_len))
            return (pat + "\n" + sub).encode("ascii", errors="ignore")

    def _minimize_input(self, is_crash, data, time_budget):
        start = time.time()
        changed = True
        while changed and (time.time() - start) < time_budget:
            changed = False
            n = len(data)
            if n <= 1:
                break
            for i in range(n):
                if (time.time() - start) >= time_budget:
                    break
                candidate = data[:i] + data[i + 1 :]
                if not candidate:
                    continue
                if is_crash(candidate):
                    data = candidate
                    changed = True
                    break
        return data

    def _find_poc(self, binary_path):
        start_time = time.time()
        time_budget = self.FUZZ_TIME_BUDGET

        def is_crash(d):
            return self._run_and_check_crash(binary_path, d)

        poc = None

        # Stage 1: dictionary-based candidates
        for data in self._generate_candidate_inputs():
            if time.time() - start_time > time_budget:
                break
            if is_crash(data):
                poc = data
                break

        # Stage 2: random fuzzing
        while poc is None and (time.time() - start_time) < time_budget:
            data = self._random_input()
            if is_crash(data):
                poc = data
                break

        # Stage 3: simple minimization
        if poc is not None:
            remaining = time_budget - (time.time() - start_time)
            if remaining > 2.0 and len(poc) > 8:
                poc = self._minimize_input(is_crash, poc, remaining - 1.0)
        return poc
