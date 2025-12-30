import os
import tarfile
import tempfile
import subprocess
import time
import random
import shutil
import hashlib


def extract_tarball(src_path: str) -> str:
    extract_dir = tempfile.mkdtemp(prefix="autopoc_src_")
    try:
        with tarfile.open(src_path, "r:*") as tf:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                return os.path.commonpath([abs_directory]) == os.path.commonpath(
                    [abs_directory, abs_target]
                )

            def safe_extract(tar, path="."):
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        continue
                tar.extractall(path)

            safe_extract(tf, extract_dir)
    except Exception:
        # If extraction fails for some reason, just leave directory empty
        pass
    return extract_dir


def detect_project_root(extract_dir: str) -> str:
    try:
        entries = [
            os.path.join(extract_dir, n)
            for n in os.listdir(extract_dir)
            if not n.startswith(".")
        ]
    except FileNotFoundError:
        return extract_dir
    if len(entries) == 1 and os.path.isdir(entries[0]):
        return entries[0]
    return extract_dir


def find_vuln_root(root: str) -> str:
    try:
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isdir(p):
                lower = name.lower()
                if any(k in lower for k in ("vuln", "bug", "old", "unsafe")):
                    return p
    except FileNotFoundError:
        pass
    return root


def list_sources(root: str):
    sources = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in (".c", ".cc", ".cpp", ".cxx"):
                sources.append(os.path.join(dirpath, f))
    return sources


def read_file_text(path: str):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def detect_main_and_fuzzer(sources):
    main_files = []
    fuzzer_files = []
    for path in sources:
        text = read_file_text(path)
        if "main(" in text:
            main_files.append(path)
        if "LLVMFuzzerTestOneInput" in text:
            fuzzer_files.append(path)
    return main_files, fuzzer_files


def create_fuzzer_adapter(root: str) -> str:
    adapter_path = os.path.join(root, "autopoc_fuzz_main.cpp")
    if not os.path.exists(adapter_path):
        code = r'''
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <vector>

int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);

static std::vector<uint8_t> read_all(FILE *f) {
    std::vector<uint8_t> buf;
    uint8_t tmp[4096];
    size_t n;
    while ((n = std::fread(tmp, 1, sizeof(tmp), f)) > 0) {
        buf.insert(buf.end(), tmp, tmp + n);
    }
    return buf;
}

int main(int argc, char **argv) {
    std::vector<uint8_t> data;
    if (argc > 1) {
        FILE *f = std::fopen(argv[1], "rb");
        if (!f) return 0;
        data = read_all(f);
        std::fclose(f);
    } else {
        data = read_all(stdin);
    }
    if (!data.empty()) {
        LLVMFuzzerTestOneInput(data.data(), data.size());
    } else {
        uint8_t dummy = 0;
        LLVMFuzzerTestOneInput(&dummy, 0);
    }
    return 0;
}
'''
        try:
            with open(adapter_path, "w") as f:
                f.write(code)
        except Exception:
            return adapter_path
    return adapter_path


def find_compiler(candidates):
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def prioritize_mains(main_files, preferred=None):
    def score(path):
        name = os.path.basename(path).lower()
        s = 0
        if preferred and os.path.abspath(path) == os.path.abspath(preferred):
            s -= 100
        keywords = [
            "poc",
            "fuzz",
            "demo",
            "test",
            "main",
            "driver",
            "uaf",
            "heap",
            "bug",
            "cue",
            "cuesheet",
        ]
        for k in keywords:
            if k in name:
                s -= 10
        depth = path.count(os.sep)
        s += depth
        return s

    return sorted(main_files, key=score)


def compile_harness(project_root: str, sources, main_candidates):
    c_compiler = find_compiler(["gcc", "clang"])
    cpp_compiler = find_compiler(["g++", "clang++", "c++"])
    if c_compiler is None and cpp_compiler is None:
        return None, None
    if c_compiler is None:
        c_compiler = cpp_compiler
    if cpp_compiler is None:
        cpp_compiler = c_compiler

    build_dir = tempfile.mkdtemp(prefix="autopoc_build_")
    for main_file in main_candidates:
        try:
            objects = []
            any_cpp = False
            main_abs = os.path.abspath(main_file)
            other_mains = {os.path.abspath(m) for m in main_candidates if m != main_file}
            compile_failed = False
            for src in sources:
                src_abs = os.path.abspath(src)
                if src_abs in other_mains:
                    continue
                ext = os.path.splitext(src)[1].lower()
                is_cpp = ext in (".cc", ".cpp", ".cxx", ".c++")
                compiler = cpp_compiler if is_cpp else c_compiler
                if compiler is None:
                    compile_failed = True
                    break
                if is_cpp:
                    any_cpp = True
                obj_name = hashlib.md5(src_abs.encode("utf-8")).hexdigest() + ".o"
                obj_path = os.path.join(build_dir, obj_name)
                cmd = [compiler, "-c", "-g", "-O1", "-fno-omit-frame-pointer", "-fsanitize=address"]
                if not is_cpp:
                    cmd.append("-std=c11")
                else:
                    cmd.append("-std=c++17")
                cmd += ["-I", project_root, "-o", obj_path, src_abs]
                try:
                    res = subprocess.run(
                        cmd,
                        cwd=project_root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                except Exception:
                    compile_failed = True
                    break
                if res.returncode != 0:
                    compile_failed = True
                    break
                objects.append(obj_path)
            if compile_failed or not objects:
                continue
            linker = cpp_compiler if any_cpp else c_compiler
            if linker is None:
                continue
            harness_path = os.path.join(build_dir, "harness_bin")
            link_cmd = [
                linker,
                "-g",
                "-O1",
                "-fno-omit-frame-pointer",
                "-fsanitize=address",
                "-o",
                harness_path,
            ] + objects + ["-lm", "-lz", "-lpthread"]
            try:
                res = subprocess.run(
                    link_cmd,
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except Exception:
                continue
            if res.returncode == 0 and os.path.exists(harness_path):
                return harness_path, build_dir
        except Exception:
            continue
    shutil.rmtree(build_dir, ignore_errors=True)
    return None, None


def build_asan_env():
    env = os.environ.copy()
    extra = "abort_on_error=1:detect_leaks=0:halt_on_error=1:allocator_may_return_null=1:symbolize=0"
    cur = env.get("ASAN_OPTIONS")
    if cur:
        env["ASAN_OPTIONS"] = cur + ":" + extra
    else:
        env["ASAN_OPTIONS"] = extra
    return env


def run_harness(harness_path: str, mode: str, data: bytes, timeout: float = 1.0):
    env = build_asan_env()
    if mode == "stdin":
        try:
            res = subprocess.run(
                [harness_path],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                env=env,
            )
            return res
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None
    else:
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(prefix="autopoc_input_")
            os.write(fd, data)
            os.close(fd)
            res = subprocess.run(
                [harness_path, tmp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                env=env,
            )
            return res
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def is_crash_result(res: subprocess.CompletedProcess):
    if res is None:
        return False
    if res.returncode == 0:
        return False
    out = (res.stdout or b"") + (res.stderr or b"")
    text = ""
    try:
        text = out.decode("latin1", errors="ignore")
    except Exception:
        text = ""
    keywords = [
        "AddressSanitizer",
        "heap-use-after-free",
        "heap buffer overflow",
        "stack-buffer-overflow",
        "double free",
        "==ERROR:",
        "runtime error",
        "Segmentation fault",
        "SIGSEGV",
    ]
    for k in keywords:
        if k in text:
            return True
    return False


def mutate(data: bytes, max_len: int = 512) -> bytes:
    if not data:
        data = os.urandom(random.randint(1, 64))
    ba = bytearray(data)
    n_mut = 1 + random.randint(0, 3)
    for _ in range(n_mut):
        op = random.randint(0, 3)
        if op == 0 and len(ba) > 0:
            idx = random.randrange(len(ba))
            bit = 1 << random.randrange(8)
            ba[idx] ^= bit
        elif op == 1 and len(ba) > 0:
            idx = random.randrange(len(ba))
            ba[idx] = random.randrange(256)
        elif op == 2 and len(ba) < max_len:
            pos = random.randrange(len(ba) + 1)
            insert_len = random.randint(1, 8)
            ba[pos:pos] = os.urandom(insert_len)
        elif op == 3 and len(ba) > 1:
            start = random.randrange(len(ba))
            end = min(len(ba), start + random.randint(1, min(8, len(ba) - start)))
            del ba[start:end]
    if len(ba) > max_len:
        del ba[max_len:]
    return bytes(ba)


def fuzz_for_crash(harness_path: str, time_budget: float = 15.0):
    seeds = [
        b"",
        b"A",
        b"\x00" * 4,
        b"\xff" * 4,
        b'FILE "test.wav" WAVE\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n',
        (
            b'FILE "test.wav" WAVE\n'
            b"  TRACK 01 AUDIO\n"
            b"    INDEX 01 00:00:00\n"
            b"  TRACK 02 AUDIO\n"
            b"    INDEX 01 03:00:00\n"
        ),
        b"--append-seekpoint=0.0 --import-cuesheet-from=cuefile.cue\n",
    ]
    modes = ("file", "stdin")
    start = time.time()

    def test_input(data: bytes):
        for mode in modes:
            res = run_harness(harness_path, mode, data, timeout=1.0)
            if is_crash_result(res):
                return data, mode
        return None, None

    for s in list(seeds):
        data, mode = test_input(s)
        if data is not None:
            return data, mode

    while time.time() - start < time_budget:
        base = random.choice(seeds)
        candidate = mutate(base)
        data, mode = test_input(candidate)
        if data is not None:
            return data, mode
        seeds.append(candidate)
        if len(seeds) > 128:
            seeds.pop(0)
    return None, None


def minimize_input(data: bytes, harness_path: str, mode: str, time_budget: float = 5.0):
    start = time.time()
    best = data
    changed = True

    def still_crashes(d: bytes):
        if not d:
            return False
        res = run_harness(harness_path, mode, d, timeout=1.0)
        return is_crash_result(res)

    while changed and time.time() - start < time_budget:
        changed = False
        length = len(best)
        if length <= 1:
            break
        chunk_sizes = [
            max(1, length // 2),
            max(1, length // 4),
            16,
            8,
            4,
            2,
            1,
        ]
        for chunk in chunk_sizes:
            if chunk <= 0 or chunk > len(best):
                continue
            pos = 0
            while pos < len(best):
                if time.time() - start > time_budget:
                    return best
                end = min(len(best), pos + chunk)
                candidate = best[:pos] + best[end:]
                if not candidate:
                    pos += chunk
                    continue
                if still_crashes(candidate):
                    best = candidate
                    changed = True
                    break
                pos += chunk
            if changed:
                break
    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        random.seed(0)
        extract_dir = extract_tarball(src_path)
        harness_path = None
        build_dir = None
        try:
            project_root = detect_project_root(extract_dir)
            vuln_root = find_vuln_root(project_root)
            sources = list_sources(vuln_root)
            if not sources:
                return b"A" * 10

            main_files, fuzzer_files = detect_main_and_fuzzer(sources)
            adapter = None
            if not main_files and fuzzer_files:
                adapter = create_fuzzer_adapter(vuln_root)
                if os.path.exists(adapter):
                    sources.append(adapter)
                    main_files = [adapter]

            if not main_files:
                return b"A" * 10

            prioritized = prioritize_mains(main_files, preferred=adapter)
            harness_path, build_dir = compile_harness(vuln_root, sources, prioritized)
            if not harness_path or not os.path.exists(harness_path):
                return b"A" * 10

            crash_data, mode = fuzz_for_crash(harness_path, time_budget=15.0)
            if crash_data is None:
                return b"A" * 10

            minimized = minimize_input(crash_data, harness_path, mode, time_budget=5.0)
            # Ensure bytes and non-empty; if minimization removed everything, keep original crash_data
            if not minimized:
                minimized = crash_data
            return minimized
        finally:
            try:
                if build_dir:
                    shutil.rmtree(build_dir, ignore_errors=True)
            except Exception:
                pass
            try:
                shutil.rmtree(extract_dir, ignore_errors=True)
            except Exception:
                pass