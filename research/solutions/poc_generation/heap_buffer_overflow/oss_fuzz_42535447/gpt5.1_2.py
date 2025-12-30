import os
import tarfile
import tempfile
import subprocess
import shutil
import random
import time


class Solution:
    def solve(self, src_path: str) -> bytes:
        default_poc = b"A" * 133
        work_dir = tempfile.mkdtemp(prefix="solver_")
        try:
            # Extract the tarball
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    tar.extractall(work_dir)
            except Exception:
                return default_poc

            # Determine root directory (handle tarballs with a single top-level dir)
            try:
                entries = [e for e in os.listdir(work_dir) if not e.startswith(".")]
                if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
                    root_dir = os.path.join(work_dir, entries[0])
                else:
                    root_dir = work_dir
            except Exception:
                return default_poc

            # Locate the fuzzer harness (file containing LLVMFuzzerTestOneInput)
            harness_src = None
            c_files = []
            cpp_files = []
            cxx_exts = (".cc", ".cpp", ".cxx", ".c++", ".cp")

            for dirpath, dirnames, filenames in os.walk(root_dir):
                for fn in filenames:
                    ext = os.path.splitext(fn)[1].lower()
                    full_path = os.path.join(dirpath, fn)
                    if ext == ".c" or ext in cxx_exts:
                        try:
                            with open(full_path, "rb") as f:
                                data = f.read()
                        except Exception:
                            data = b""
                        if b"LLVMFuzzerTestOneInput" in data:
                            # Prefer C++ harness if available
                            if harness_src is None or ext in cxx_exts:
                                harness_src = full_path
                    if ext == ".c":
                        c_files.append(full_path)
                    elif ext in cxx_exts:
                        cpp_files.append(full_path)

            if harness_src is None:
                return default_poc

            # Add a simple runner that reads a file and calls LLVMFuzzerTestOneInput
            runner_cpp_path = os.path.join(root_dir, "poc_runner.cpp")
            try:
                with open(runner_cpp_path, "w", encoding="utf-8") as f:
                    f.write(
                        "#include <cstddef>\n"
                        "#include <cstdint>\n"
                        "#include <vector>\n"
                        "#include <fstream>\n"
                        "#include <iostream>\n\n"
                        "extern \"C\" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size);\n\n"
                        "int main(int argc, char** argv) {\n"
                        "    std::ios::sync_with_stdio(false);\n"
                        "    std::cin.tie(nullptr);\n"
                        "    if (argc != 2) {\n"
                        "        return 1;\n"
                        "    }\n"
                        "    const char* path = argv[1];\n"
                        "    std::ifstream in(path, std::ios::binary);\n"
                        "    if (!in) {\n"
                        "        return 1;\n"
                        "    }\n"
                        "    std::vector<uint8_t> data((std::istreambuf_iterator<char>(in)),\n"
                        "                              std::istreambuf_iterator<char>());\n"
                        "    const uint8_t* ptr = data.empty() ? nullptr : data.data();\n"
                        "    return LLVMFuzzerTestOneInput(ptr, data.size());\n"
                        "}\n"
                    )
            except Exception:
                return default_poc

            cpp_files.append(runner_cpp_path)

            # Collect include directories
            src_files = c_files + cpp_files
            include_dirs = sorted({os.path.dirname(p) or "." for p in src_files})
            include_flags = []
            for d in include_dirs:
                include_flags.extend(["-I", d])

            cxx = os.environ.get("CXX", "clang++")
            cc = os.environ.get("CC", "clang")

            common_cxxflags = [
                "-std=c++17",
                "-O1",
                "-g",
                "-fsanitize=address",
                "-fno-omit-frame-pointer",
                "-DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION",
                "-pthread",
            ]
            common_cflags = [
                "-O1",
                "-g",
                "-fsanitize=address",
                "-fno-omit-frame-pointer",
                "-DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION",
                "-pthread",
            ]

            env = os.environ.copy()

            build_dir = os.path.join(root_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            objs = []

            def compile_one(src: str, is_cxx: bool) -> str | None:
                obj_name = os.path.basename(src) + ".o"
                obj_path = os.path.join(build_dir, obj_name)
                if is_cxx:
                    cmd = [cxx] + common_cxxflags + include_flags + ["-c", src, "-o", obj_path]
                else:
                    cmd = [cc] + common_cflags + include_flags + ["-c", src, "-o", obj_path]
                try:
                    subprocess.run(
                        cmd,
                        cwd=root_dir,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                except Exception:
                    return None
                return obj_path

            def has_main(src: str) -> bool:
                if src == runner_cpp_path:
                    return False
                try:
                    with open(src, "rb") as f:
                        data = f.read()
                except Exception:
                    return False
                return b" main(" in data or b"\nmain(" in data or b"\r\nmain(" in data

            # Compile C++ sources
            for src in cpp_files:
                if src != runner_cpp_path and has_main(src):
                    continue
                is_harness = src == harness_src
                obj = compile_one(src, is_cxx=True)
                if obj is None:
                    # Fallback: try compiling as C
                    obj = compile_one(src, is_cxx=False)
                    if obj is None:
                        if is_harness:
                            return default_poc
                        else:
                            continue
                objs.append(obj)

            # Compile C sources
            for src in c_files:
                if has_main(src):
                    continue
                is_harness = src == harness_src
                obj = compile_one(src, is_cxx=False)
                if obj is None:
                    # Fallback: try compiling as C++
                    obj = compile_one(src, is_cxx=True)
                    if obj is None:
                        if is_harness:
                            return default_poc
                        else:
                            continue
                objs.append(obj)

            if not objs:
                return default_poc

            # Link the binary
            binary = os.path.join(root_dir, "poc_runner_bin")
            link_cmd = [cxx] + common_cxxflags + objs + ["-o", binary, "-lm"]
            try:
                subprocess.run(
                    link_cmd,
                    cwd=root_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
            except Exception:
                return default_poc

            random.seed(0)
            inp_path = os.path.join(root_dir, "input.bin")

            def run_candidate(data: bytes) -> int:
                try:
                    with open(inp_path, "wb") as f:
                        f.write(data)
                except Exception:
                    return 0
                try:
                    result = subprocess.run(
                        [binary, inp_path],
                        cwd=root_dir,
                        env=dict(
                            env,
                            ASAN_OPTIONS="abort_on_error=1:detect_leaks=0:allocator_may_return_null=1",
                        ),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=0.5,
                    )
                    return result.returncode
                except subprocess.TimeoutExpired:
                    # Treat timeout as crash
                    return -1
                except Exception:
                    return 0

            def is_crash(data: bytes) -> bool:
                rc = run_candidate(data)
                return rc < 0

            # Try a few simple seeds first
            seeds = [
                b"",
                b"\x00" * 4,
                b"\x00" * 133,
                b"A" * 133,
                bytes(range(256))[:133],
            ]
            best = None
            for s in seeds:
                if is_crash(s):
                    best = s
                    break

            max_iters = 1500
            start_time = time.time()

            for i in range(max_iters):
                if best is not None:
                    break
                r = random.random()
                if r < 0.6:
                    length = 133
                elif r < 0.85:
                    length = random.randint(64, 256)
                else:
                    length = random.randint(1, 512)

                buf = bytearray(os.urandom(length))

                # Inject large values to trigger potential unsigned underflows
                if length >= 8:
                    if i % 2 == 0:
                        buf[0:4] = b"\xff\xff\xff\xff"
                        buf[4:8] = b"\x00\x00\x00\x10"
                    else:
                        buf[0:4] = b"\xff\xff\xff\xff"
                        buf[4:8] = b"\xff\xff\xff\x7f"

                # Add a simple structured pattern occasionally
                if length >= 16 and i % 3 == 0:
                    buf[8:12] = b"GMAP"
                    buf[12:16] = (1).to_bytes(4, "little")

                candidate = bytes(buf)
                if is_crash(candidate):
                    best = candidate
                    break

                if time.time() - start_time > 25:
                    break

            if best is None:
                return default_poc

            # Quick minimization: trim from the end while preserving crash
            data = best
            min_start = time.time()
            while len(data) > 1 and time.time() - min_start < 10:
                changed = False
                for chunk in [len(data) // 2, 64, 32, 16, 8, 4, 2, 1]:
                    if chunk <= 0 or chunk >= len(data):
                        continue
                    candidate = data[:-chunk]
                    if is_crash(candidate):
                        data = candidate
                        changed = True
                        break
                if not changed:
                    break

            return data
        finally:
            try:
                shutil.rmtree(work_dir)
            except Exception:
                pass