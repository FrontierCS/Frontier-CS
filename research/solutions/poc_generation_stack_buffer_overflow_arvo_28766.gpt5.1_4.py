import os
import tarfile
import tempfile
import subprocess
import time
import random
import re
import shutil
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        workdir = tempfile.mkdtemp(prefix="pocgen_")

        def cleanup():
            shutil.rmtree(workdir, ignore_errors=True)

        def determine_root(base: str) -> str:
            try:
                entries = [e for e in os.listdir(base) if e not in ('.', '..', '__MACOSX')]
            except Exception:
                return base
            dirs = [e for e in entries if os.path.isdir(os.path.join(base, e))]
            if len(dirs) == 1 and len(entries) == 1:
                return os.path.join(base, dirs[0])
            return base

        def list_all_files(root: str):
            res = []
            for r, _d, files in os.walk(root):
                for f in files:
                    res.append(os.path.join(r, f))
            return res

        def is_elf(path: str) -> bool:
            try:
                with open(path, "rb") as f:
                    sig = f.read(4)
                return sig == b"\x7fELF"
            except Exception:
                return False

        def try_compile(src_files, out_path: str) -> bool:
            if not src_files:
                return False
            cc = shutil.which("g++") or shutil.which("clang++")
            if not cc:
                return False

            def run_cmd(extra_flags):
                cmd = [cc, "-std=c++17", "-g", "-O0", "-pthread"] + extra_flags
                cmd += src_files
                cmd += ["-o", out_path]
                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=src_root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                    )
                    return proc.returncode == 0 and os.path.exists(out_path)
                except Exception:
                    return False

            # First try with ASan
            if run_cmd(["-fsanitize=address"]):
                return True
            # Fallback without sanitizer
            if run_cmd([]):
                return True
            return False

        def build_via_script(root: str):
            bin_candidates = []
            scripts = []
            for r, _d, files in os.walk(root):
                if "build.sh" in files:
                    scripts.append(os.path.join(r, "build.sh"))

            if not scripts:
                return bin_candidates

            for script in scripts:
                before_files = set(list_all_files(root))
                base_env = os.environ.copy()
                # Try ASan first, then without
                for with_asan in (True, False):
                    env = base_env.copy()
                    common = " -g -O0"
                    if with_asan:
                        san = " -fsanitize=address"
                    else:
                        san = ""
                    for var in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
                        env[var] = env.get(var, "") + common + san
                    try:
                        subprocess.run(
                            ["bash", script],
                            cwd=os.path.dirname(script),
                            env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=180,
                        )
                    except Exception:
                        continue
                    after_files = set(list_all_files(root))
                    new_files = [p for p in (after_files - before_files) if os.path.isfile(p)]
                    for p in new_files:
                        try:
                            st = os.stat(p)
                        except Exception:
                            continue
                        if not (st.st_mode & stat.S_IXUSR):
                            continue
                        if is_elf(p):
                            bin_candidates.append(p)
                    if bin_candidates:
                        return bin_candidates
            return bin_candidates

        def compile_harnesses(root: str):
            harness_files = []
            main_files = []
            for r, _d, files in os.walk(root):
                for name in files:
                    if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".C", ".c++")):
                        continue
                    path = os.path.join(r, name)
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    if b"LLVMFuzzerTestOneInput" in data:
                        harness_files.append(path)
                    if re.search(br"\bint\s+main\s*\(", data):
                        main_files.append(path)

            bin_candidates = []

            # Compile harnesses with LLVMFuzzerTestOneInput
            for idx, path in enumerate(harness_files):
                out_bin = os.path.join(root, f"auto_harness_{idx}")
                if try_compile([path], out_bin):
                    bin_candidates.append(out_bin)

            # Compile mains (limit number)
            max_mains = 6
            for idx, path in enumerate(main_files[:max_mains]):
                out_bin = os.path.join(root, f"auto_main_{idx}")
                dir_path = os.path.dirname(path)
                extra = []
                try:
                    for name in os.listdir(dir_path):
                        if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".C", ".c++")):
                            continue
                        full = os.path.join(dir_path, name)
                        if full == path:
                            continue
                        extra.append(full)
                except Exception:
                    pass
                srcs = [path] + extra
                if try_compile(srcs, out_bin):
                    bin_candidates.append(out_bin)

            return bin_candidates

        def collect_seeds(root: str, max_files: int = 64, max_size: int = 1024 * 1024):
            seeds = []
            seed_paths = []
            interesting_dirs = {
                "corpus",
                "seed_corpus",
                "seeds",
                "inputs",
                "input",
                "tests",
                "test",
                "data",
                "examples",
                "example",
                "sample",
                "samples",
                "testdata",
            }
            exclude_exts = {
                ".c",
                ".cc",
                ".cpp",
                ".cxx",
                ".C",
                ".c++",
                ".h",
                ".hh",
                ".hpp",
                ".hxx",
                ".py",
                ".java",
                ".sh",
                ".bat",
                ".ps1",
                ".pl",
                ".rb",
                ".php",
                ".go",
                ".rs",
                ".js",
                ".ts",
                ".html",
                ".htm",
                ".css",
                ".xml",
                ".json5",
                ".md",
                ".txt",
                ".rst",
                ".yml",
                ".yaml",
                ".toml",
                ".ini",
                ".cfg",
                ".cmake",
                ".in",
                ".am",
                ".ac",
            }
            for r, _d, files in os.walk(root):
                base = os.path.basename(r).lower()
                if base not in interesting_dirs:
                    continue
                for name in files:
                    path = os.path.join(r, name)
                    try:
                        if not os.path.isfile(path):
                            continue
                        sz = os.path.getsize(path)
                    except Exception:
                        continue
                    if sz <= 0 or sz > max_size:
                        continue
                    ext = os.path.splitext(name)[1].lower()
                    if ext in exclude_exts:
                        continue
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    seeds.append(data)
                    seed_paths.append(path)
                    if len(seeds) >= max_files:
                        return seeds, seed_paths
            if not seeds:
                seeds = [b""]  # fallback seed
            return seeds, seed_paths

        def is_textual(data: bytes) -> bool:
            if not data:
                return False
            printable = 0
            for b in data:
                if 32 <= b < 127 or b in (9, 10, 13):
                    printable += 1
            return printable / len(data) > 0.85

        def mutate_text_numbers(data: bytes) -> bytes:
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                return None
            matches = list(re.finditer(r"\d+", text))
            if not matches:
                return None
            vals = []
            for m in matches:
                try:
                    vals.append(int(m.group()))
                except Exception:
                    continue
            if not vals:
                return None
            max_val = max(vals) if vals else 1
            k = random.randint(1, min(4, len(matches)))
            chosen_idx = random.sample(range(len(matches)), k)
            chosen_matches = [matches[i] for i in chosen_idx]
            chosen_matches.sort(key=lambda m: m.start(), reverse=True)
            new_text = text
            for m in chosen_matches:
                try:
                    new_val = str(max_val + random.randint(10, 10000))
                except Exception:
                    new_val = "0"
                new_text = new_text[: m.start()] + new_val + new_text[m.end() :]
            try:
                return new_text.encode("utf-8")
            except Exception:
                return data

        def mutate_bytes(data: bytes, max_len: int = 4096) -> bytes:
            if not data:
                data = bytearray(os.urandom(32))
            else:
                data = bytearray(data)
            num_mut = random.randint(1, max(1, len(data) // 16))
            for _ in range(num_mut):
                choice = random.random()
                if choice < 0.34:
                    # bit flip
                    if not data:
                        continue
                    idx = random.randrange(len(data))
                    bit = 1 << random.randrange(8)
                    data[idx] ^= bit
                elif choice < 0.67:
                    # insert
                    idx = random.randrange(len(data) + 1)
                    data.insert(idx, random.randrange(256))
                else:
                    # delete range
                    if len(data) > 1:
                        start = random.randrange(len(data))
                        end = start + random.randint(1, min(8, len(data) - start))
                        del data[start:end]
            if len(data) > max_len:
                del data[max_len:]
            if not data:
                data = bytearray(os.urandom(16))
            return bytes(data)

        def run_target(bin_path: str, data: bytes, mode: str):
            # mode: "stdin" or "arg"
            try:
                if mode == "stdin":
                    proc = subprocess.run(
                        [bin_path],
                        input=data,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=2,
                    )
                else:
                    tmp_fd, tmp_path = tempfile.mkstemp(dir=workdir)
                    try:
                        os.write(tmp_fd, data)
                    finally:
                        os.close(tmp_fd)
                    try:
                        proc = subprocess.run(
                            [bin_path, tmp_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=2,
                        )
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
            except subprocess.TimeoutExpired:
                return False, None
            except Exception:
                return False, None

            crashed = False
            if proc.returncode is not None and proc.returncode < 0:
                crashed = True
            if b"AddressSanitizer" in proc.stderr or b"AddressSanitizer" in proc.stdout:
                crashed = True
            return crashed, proc

        def fuzz_binaries(bin_candidates):
            if not bin_candidates:
                return None
            seeds, _seed_paths = collect_seeds(src_root)
            start_time = time.time()
            max_time = 70.0  # seconds for fuzzing

            # Quick try seeds without mutation
            for bin_path in bin_candidates:
                for mode in ("stdin", "arg"):
                    for data in seeds:
                        crashed, _ = run_target(bin_path, data, mode)
                        if crashed:
                            return data

            # Fuzzing
            for bin_path in bin_candidates:
                for mode in ("stdin", "arg"):
                    iters = 0
                    while time.time() - start_time < max_time and iters < 8000:
                        base = random.choice(seeds) if seeds else os.urandom(32)
                        if is_textual(base):
                            mutated = mutate_text_numbers(base)
                            if mutated is None:
                                mutated = mutate_bytes(base)
                        else:
                            mutated = mutate_bytes(base)
                        crashed, _ = run_target(bin_path, mutated, mode)
                        iters += 1
                        if crashed:
                            return mutated
            return None

        try:
            with tarfile.open(src_path, "r:*") as tar:
                tar.extractall(workdir)
            src_root = determine_root(workdir)

            # 1. Try build.sh scripts
            bin_candidates = build_via_script(src_root)

            # 2. Try direct compilation of harnesses / mains if needed
            if not bin_candidates:
                bin_candidates = compile_harnesses(src_root)

            # 3. Fuzz to find PoC
            poc = fuzz_binaries(bin_candidates)

            # 4. Fallback generic payload if nothing found
            if poc is None:
                # Overlong input, hoping for generic overflow if any
                poc = b"A" * 256

            return poc
        finally:
            cleanup()