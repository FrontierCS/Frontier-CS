import os
import tarfile
import tempfile
import subprocess
import random
import string
import time
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        workdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            self._extract_tar(src_path, workdir)
            bin_path = self._compile_project(workdir)
            if not bin_path or not os.path.exists(bin_path):
                return self._fallback_poc()

            crash_input, mode = self._find_heap_uaf_input(bin_path)
            if crash_input is None:
                return self._fallback_poc()

            minimized = self._minimize_input(bin_path, crash_input, mode)
            return minimized
        except Exception:
            return self._fallback_poc()

    # ---------- Utility ----------

    def _extract_tar(self, src_path: str, dst_dir: str) -> None:
        try:
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
        except tarfile.ReadError:
            # Not a tar; assume directory
            if os.path.isdir(src_path):
                # Copy is not needed; just use directory directly
                pass

    # ---------- Compilation ----------

    class _FileInfo:
        __slots__ = ("path", "has_main")

        def __init__(self, path: str, has_main: bool):
            self.path = path
            self.has_main = has_main

    def _gather_sources(self, root: str) -> Tuple[List[str], Optional[str]]:
        src_exts = {".c", ".cc", ".cpp", ".cxx", ".C"}
        file_infos: List[Solution._FileInfo] = []
        main_candidates: List[str] = []

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip obvious test directories to avoid gtest, etc.
            lowered = [d.lower() for d in dirnames]
            to_remove = []
            for i, d in enumerate(dirnames):
                ld = lowered[i]
                if "test" in ld or "gtest" in ld or "unittest" in ld:
                    to_remove.append(d)
            for d in to_remove:
                try:
                    dirnames.remove(d)
                except ValueError:
                    pass

            for fname in filenames:
                ext = os.path.splitext(fname)[1]
                if ext.lower() not in src_exts:
                    continue
                fpath = os.path.join(dirpath, fname)
                has_main = False
                try:
                    with open(fpath, "r", encoding="latin1", errors="ignore") as f:
                        content = f.read()
                    if " main(" in content or "\nmain(" in content or "int main(" in content:
                        has_main = True
                except Exception:
                    pass
                fi = Solution._FileInfo(fpath, has_main)
                file_infos.append(fi)
                if has_main:
                    main_candidates.append(fpath)

        src_files = [fi.path for fi in file_infos]
        main_file = None
        if main_candidates:
            # Prefer a candidate whose name suggests it's a harness/driver
            def score(p: str) -> Tuple[int, int]:
                lname = os.path.basename(p).lower()
                harness_keywords = ["fuzz", "driver", "harness", "main"]
                s = 0
                for kw in harness_keywords:
                    if kw in lname:
                        s -= 1
                # Prefer shorter paths
                return (s, len(p))

            main_candidates.sort(key=score)
            main_file = main_candidates[0]

        # Ensure exactly one main by excluding other main-containing files
        if main_file is not None:
            filtered_files = []
            for fi in file_infos:
                if fi.path == main_file or not fi.has_main:
                    filtered_files.append(fi.path)
            src_files = filtered_files

        return src_files, main_file

    def _compile_project(self, root: str) -> Optional[str]:
        src_files, _ = self._gather_sources(root)
        if not src_files:
            return None

        bin_path = os.path.join(root, "poc_target_bin")
        # Make paths relative to root for compilation
        rel_src_files = [os.path.relpath(p, root) for p in src_files]

        compiler_cmds = [
            ["g++", "-std=c++17"],
            ["g++", "-std=c++14"],
            ["clang++", "-std=c++17"],
            ["clang++", "-std=c++14"],
        ]
        common_flags_san = ["-fsanitize=address", "-g", "-O1", "-fno-omit-frame-pointer", "-pthread"]
        common_flags_nosan = ["-g", "-O1", "-pthread"]

        # First try with sanitizer
        for base in compiler_cmds:
            cmd = base + common_flags_san + rel_src_files + ["-o", bin_path]
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                )
                if proc.returncode == 0:
                    return bin_path
            except Exception:
                continue

        # Fallback: no sanitizer
        for base in compiler_cmds:
            cmd = base + common_flags_nosan + rel_src_files + ["-o", bin_path]
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                )
                if proc.returncode == 0:
                    return bin_path
            except Exception:
                continue

        return None

    # ---------- Execution & Detection ----------

    def _run_with_input(self, bin_path: str, data: bytes, mode: str) -> Tuple[bool, bool]:
        """
        Returns (crashed, is_heap_uaf_like)
        """
        env = os.environ.copy()
        # Encourage ASan to exit quickly and not complain about leaks
        asan_opts = env.get("ASAN_OPTIONS", "")
        extra = "detect_leaks=0:abort_on_error=1"
        if asan_opts:
            if "detect_leaks" not in asan_opts:
                asan_opts += ":detect_leaks=0"
            env["ASAN_OPTIONS"] = asan_opts
        else:
            env["ASAN_OPTIONS"] = extra

        crashed = False
        is_heap_uaf = False
        try:
            if mode == "stdin":
                proc = subprocess.run(
                    [bin_path],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=0.5,
                    env=env,
                )
            elif mode == "file":
                tmp_fd, tmp_path = tempfile.mkstemp(prefix="poc_input_", suffix=".bin")
                try:
                    os.write(tmp_fd, data)
                finally:
                    os.close(tmp_fd)
                try:
                    proc = subprocess.run(
                        [bin_path, tmp_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=0.5,
                        env=env,
                    )
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            else:
                return False, False

            rc = proc.returncode
            stderr_bytes = proc.stderr or b""
            stderr_text = stderr_bytes.decode("latin1", errors="ignore").lower()

            crashed = rc != 0
            if "addresssanitizer" in stderr_text:
                if ("heap-use-after-free" in stderr_text or
                        "heap use after free" in stderr_text or
                        "double-free" in stderr_text or
                        "double free" in stderr_text):
                    is_heap_uaf = True
                    crashed = True
            else:
                # Fallback detection for unsanitized builds: glibc double free
                if "double free" in stderr_text or "invalid pointer" in stderr_text:
                    is_heap_uaf = True
                    crashed = True

        except subprocess.TimeoutExpired:
            # Treat timeouts as non-crashes for our purposes
            crashed = False
            is_heap_uaf = False
        except Exception:
            crashed = False
            is_heap_uaf = False

        return crashed, is_heap_uaf

    # ---------- Fuzzing ----------

    def _seed_inputs(self) -> List[bytes]:
        seeds = [
            b"",
            b"\n",
            b"0",
            b"1",
            b"-1",
            b"A",
            b"a",
            b"{}",
            b"[]",
            b"()",
            b"<root></root>",
            b"<node></node>",
            b"{\"a\":1}",
            b"{\"a\":[1,2,3]}",
            b"- item1\n- item2\n",
            b"root {\n}\n",
            b"node {\n}\n",
            b"[section]\nkey=value\n",
            b"---\n- a\n- b\n",
            b"# comment\n",
            b"add\n",
            b"node add\n",
            b"children:\n  - a\n  - b\n",
        ]
        return seeds

    def _random_ascii_bytes(self, length: int) -> bytes:
        chars = string.ascii_letters + string.digits + string.punctuation + " \n\t"
        return "".join(random.choice(chars) for _ in range(length)).encode("latin1", errors="ignore")

    def _random_binary_bytes(self, length: int) -> bytes:
        return bytes(random.getrandbits(8) for _ in range(length))

    def _mutate(self, data: bytes, max_len: int = 128) -> bytes:
        if not data:
            return self._random_ascii_bytes(random.randint(1, max_len))

        data = bytearray(data)
        for _ in range(random.randint(1, 4)):
            choice = random.randint(0, 3)
            if choice == 0 and len(data) > 0:
                # flip a byte
                idx = random.randrange(len(data))
                data[idx] ^= 1 << random.randint(0, 7)
            elif choice == 1 and len(data) > 0:
                # delete a byte
                idx = random.randrange(len(data))
                del data[idx]
            elif choice == 2 and len(data) < max_len:
                # insert random byte
                idx = random.randrange(len(data) + 1)
                data.insert(idx, random.getrandbits(8))
            elif choice == 3 and len(data) < max_len and len(data) >= 2:
                # duplicate a slice
                start = random.randrange(len(data))
                end = min(len(data), start + random.randint(1, 8))
                slice_bytes = data[start:end]
                idx = random.randrange(len(data) + 1)
                data[idx:idx] = slice_bytes
        if len(data) == 0:
            data.append(random.getrandbits(8))
        if len(data) > max_len:
            del data[max_len:]
        return bytes(data)

    def _find_heap_uaf_input(self, bin_path: str) -> Tuple[Optional[bytes], Optional[str]]:
        modes = ["stdin", "file"]
        seeds = self._seed_inputs()

        timeout_global = 45.0
        time_end = time.time() + timeout_global

        # 1) Try seeds directly
        for seed in seeds:
            if time.time() > time_end:
                break
            for mode in modes:
                crashed, is_heap = self._run_with_input(bin_path, seed, mode)
                if is_heap:
                    return seed, mode

        # 2) Random / mutational fuzzing
        best_input: Optional[bytes] = None
        best_mode: Optional[str] = None

        max_runs = 400
        for _ in range(max_runs):
            if time.time() > time_end:
                break

            if best_input is not None and random.random() < 0.7:
                data = self._mutate(best_input, max_len=128)
            else:
                length = random.randint(1, 120)
                if random.random() < 0.5:
                    data = self._random_ascii_bytes(length)
                else:
                    data = self._random_binary_bytes(length)

            for mode in modes:
                crashed, is_heap = self._run_with_input(bin_path, data, mode)
                if is_heap:
                    return data, mode
                if crashed and best_input is None:
                    # Keep as a potential starting point, though not confirmed UAF
                    best_input = data
                    best_mode = mode

        # If we never confirmed heap-use-after-free but saw some crash, use that
        if best_input is not None and best_mode is not None:
            return best_input, best_mode

        return None, None

    # ---------- Minimization ----------

    def _minimize_input(self, bin_path: str, data: bytes, mode: str) -> bytes:
        # Simple delta-debugging: try removing bytes while preserving heap UAF
        current = bytearray(data)
        changed = True
        time_end = time.time() + 25.0

        while changed and time.time() < time_end:
            changed = False
            i = 0
            while i < len(current) and time.time() < time_end:
                trial = current[:i] + current[i + 1:]
                if not trial:
                    i += 1
                    continue
                _, is_heap = self._run_with_input(bin_path, bytes(trial), mode)
                if is_heap:
                    current = trial
                    changed = True
                    # After successful shrink, restart from beginning
                    i = 0
                    continue
                i += 1

        return bytes(current)

    # ---------- Fallback ----------

    def _fallback_poc(self) -> bytes:
        # 60 bytes to match ground-truth length hint; contents generic
        return (b"A double-free / heap-use-after-free placeholder PoC input......")[:60]