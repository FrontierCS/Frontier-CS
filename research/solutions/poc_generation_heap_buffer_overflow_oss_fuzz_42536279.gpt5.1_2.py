import os
import tarfile
import tempfile
import subprocess
import random
import time
import re
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        random.seed(0)
        work_dir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            return self._solve_impl(src_path, work_dir)
        finally:
            try:
                shutil.rmtree(work_dir)
            except Exception:
                pass

    def _solve_impl(self, src_path: str, work_dir: str) -> bytes:
        # Extract tarball
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(work_dir)
        except Exception:
            return self._fallback_poc()

        root_dir = self._find_root_dir(work_dir)
        harness = self._find_fuzzer_file(root_dir)
        if not harness:
            return self._fallback_poc()

        lang = self._detect_language(harness, root_dir)
        compiler = self._choose_compiler(lang)
        if not compiler:
            return self._fallback_poc()

        supports_asan = self._compiler_supports_flag(compiler, "-fsanitize=address", lang)
        driver_path = self._create_driver(root_dir, harness, lang)

        sources = self._collect_source_files(root_dir, harness, driver_path)
        if not sources:
            return self._fallback_poc()

        exe_path = os.path.join(work_dir, "runner_bin")
        compiled = self._compile_project(
            compiler=compiler,
            lang=lang,
            root=root_dir,
            sources=sources,
            driver_path=driver_path,
            exe_path=exe_path,
            use_asan=supports_asan,
        )
        if not compiled:
            return self._fallback_poc()

        poc = self._fuzz_for_crash(exe_path, use_asan=supports_asan)
        if poc is not None and isinstance(poc, (bytes, bytearray)) and len(poc) > 0:
            return bytes(poc)

        return self._fallback_poc()

    def _find_root_dir(self, base: str) -> str:
        try:
            entries = [e for e in os.listdir(base) if not e.startswith(".") and e != "__MACOSX"]
        except Exception:
            return base
        if len(entries) == 1:
            main = os.path.join(base, entries[0])
            if os.path.isdir(main):
                return main
        return base

    def _find_fuzzer_file(self, root: str) -> str | None:
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".C")):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" in txt:
                    score = 0
                    lower = path.lower()
                    if "svc" in lower:
                        score += 2
                    if "dec" in lower or "decode" in lower:
                        score += 2
                    if "video" in lower or "h264" in lower:
                        score += 1
                    candidates.append((score, path))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], len(x[1])))
        return candidates[0][1]

    def _detect_language(self, harness_path: str, root: str) -> str:
        has_cpp = False
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                if name.endswith((".cc", ".cpp", ".cxx", ".C")):
                    has_cpp = True
                    break
            if has_cpp:
                break
        if harness_path.endswith(".c") and not has_cpp:
            return "c"
        return "c++"

    def _choose_compiler(self, lang: str) -> str | None:
        if lang == "c++":
            for cxx in ("clang++", "g++", "c++"):
                path = shutil.which(cxx)
                if path:
                    return path
        else:
            for cc in ("clang", "gcc", "cc"):
                path = shutil.which(cc)
                if path:
                    return path
        return None

    def _compiler_supports_flag(self, compiler: str, flag: str, lang: str) -> bool:
        code = "int main() { return 0; }\n"
        suffix = ".cpp" if lang == "c++" else ".c"
        try:
            with tempfile.TemporaryDirectory(prefix="comp_test_") as td:
                src = os.path.join(td, "test" + suffix)
                out = os.path.join(td, "test_bin")
                with open(src, "w") as f:
                    f.write(code)
                cmd = [compiler, flag, src, "-o", out]
                r = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=20,
                )
                return r.returncode == 0 and os.path.exists(out)
        except Exception:
            return False

    def _create_driver(self, root: str, harness: str, lang: str) -> str:
        driver_name = "__poc_driver.c" if lang == "c" else "__poc_driver.cpp"
        driver_path = os.path.join(root, driver_name)

        has_extern_c = False
        if lang == "c++":
            try:
                with open(harness, "r", errors="ignore") as f:
                    txt = f.read()
                if 'extern "C" int LLVMFuzzerTestOneInput' in txt:
                    has_extern_c = True
            except Exception:
                has_extern_c = False

        if lang == "c":
            extern_decl = "int LLVMFuzzerTestOneInput(const unsigned char *data, size_t size);\n"
        else:
            if has_extern_c:
                extern_decl = 'extern "C" int LLVMFuzzerTestOneInput(const unsigned char *data, size_t size);\n'
            else:
                extern_decl = "int LLVMFuzzerTestOneInput(const unsigned char *data, size_t size);\n"

        if lang == "c":
            source = f"""#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>

{extern_decl}
int main(int argc, char **argv) {{
    FILE *f = stdin;
    if (argc > 1) {{
        f = fopen(argv[1], "rb");
        if (!f) return 1;
    }}
    if (fseek(f, 0, SEEK_END) != 0) {{
        if (f != stdin) fclose(f);
        return 1;
    }}
    long sz = ftell(f);
    if (sz < 0) {{
        if (f != stdin) fclose(f);
        return 1;
    }}
    if (fseek(f, 0, SEEK_SET) != 0) {{
        if (f != stdin) fclose(f);
        return 1;
    }}
    size_t size = (size_t)sz;
    unsigned char *data = (unsigned char*)malloc(size ? size : 1);
    if (!data) {{
        if (f != stdin) fclose(f);
        return 1;
    }}
    if (size > 0) {{
        if (fread(data, 1, size, f) != size) {{
            free(data);
            if (f != stdin) fclose(f);
            return 1;
        }}
    }}
    if (f != stdin) fclose(f);
    LLVMFuzzerTestOneInput(data, size);
    free(data);
    return 0;
}}
"""
        else:
            source = f"""#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <vector>
#include <iostream>

{extern_decl}
int main(int argc, char **argv) {{
    std::vector<unsigned char> data;
    data.reserve(8192);
    if (argc > 1) {{
        std::FILE *f = std::fopen(argv[1], "rb");
        if (!f) return 1;
        if (std::fseek(f, 0, SEEK_END) != 0) {{
            std::fclose(f);
            return 1;
        }}
        long sz = std::ftell(f);
        if (sz < 0) {{
            std::fclose(f);
            return 1;
        }}
        if (std::fseek(f, 0, SEEK_SET) != 0) {{
            std::fclose(f);
            return 1;
        }}
        if (sz > 0) {{
            data.resize(static_cast<size_t>(sz));
            if (std::fread(data.data(), 1, data.size(), f) != data.size()) {{
                std::fclose(f);
                return 1;
            }}
        }}
        std::fclose(f);
    }} else {{
        std::ios::sync_with_stdio(false);
        std::cin.tie(nullptr);
        while (true) {{
            unsigned char buf[4096];
            std::cin.read(reinterpret_cast<char*>(buf), sizeof(buf));
            std::streamsize got = std::cin.gcount();
            if (got <= 0) break;
            data.insert(data.end(), buf, buf + got);
        }}
    }}
    if (!data.empty()) {{
        LLVMFuzzerTestOneInput(data.data(), data.size());
    }} else {{
        LLVMFuzzerTestOneInput(nullptr, 0);
    }}
    return 0;
}}
"""
        with open(driver_path, "w") as f:
            f.write(source)
        return driver_path

    def _collect_source_files(self, root: str, harness_path: str, driver_path: str) -> list:
        sources = []
        harness_abs = os.path.abspath(harness_path)
        driver_abs = os.path.abspath(driver_path)
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".C")):
                    continue
                path = os.path.join(dirpath, name)
                path_abs = os.path.abspath(path)
                if path_abs == driver_abs:
                    continue
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    txt = ""
                if "LLVMFuzzerTestOneInput" in txt and path_abs != harness_abs:
                    continue
                if re.search(r"\bmain\s*\(", txt):
                    continue
                sources.append(path)
        if harness_abs not in [os.path.abspath(p) for p in sources]:
            sources.append(harness_path)
        return sources

    def _compile_project(
        self,
        compiler: str,
        lang: str,
        root: str,
        sources: list,
        driver_path: str,
        exe_path: str,
        use_asan: bool,
    ) -> bool:
        include_dirs = set()
        include_dirs.add(root)
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                if name.endswith((".h", ".hpp", ".hh", ".hxx", ".inc")):
                    include_dirs.add(dirpath)
                    break
        include_flags = [f"-I{d}" for d in include_dirs]

        flags = ["-g", "-O1"]
        if lang == "c":
            flags.append("-std=c99")
        else:
            flags.append("-std=c++11")
        if use_asan:
            flags.extend(["-fsanitize=address", "-fno-omit-frame-pointer"])

        cmd = [compiler] + flags + include_flags + ["-o", exe_path, driver_path] + sources
        try:
            r = subprocess.run(
                cmd,
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )
            return r.returncode == 0 and os.path.exists(exe_path)
        except Exception:
            return False

    def _fuzz_for_crash(self, exe_path: str, use_asan: bool) -> bytes | None:
        max_time = 20.0
        timeout_per = 0.3
        start = time.time()
        seeds = self._initial_seeds()
        if not seeds:
            seeds = [self._fallback_poc()]
        tmp_input = os.path.join(os.path.dirname(exe_path), "poc_input.bin")

        env = os.environ.copy()
        if use_asan:
            extra = "detect_leaks=0:allocator_may_return_null=1:abort_on_error=1"
            prev = env.get("ASAN_OPTIONS", "")
            if prev:
                env["ASAN_OPTIONS"] = prev + ":" + extra
            else:
                env["ASAN_OPTIONS"] = extra

        last = seeds[0]
        i = 0
        while time.time() - start < max_time:
            if i < len(seeds):
                data = seeds[i]
            else:
                if random.random() < 0.7:
                    data = self._mutate(last)
                else:
                    data = self._generate_fresh()
            i += 1
            last = data

            try:
                with open(tmp_input, "wb") as f:
                    f.write(data)
            except Exception:
                continue

            try:
                r = subprocess.run(
                    [exe_path, tmp_input],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=timeout_per,
                )
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue

            if r.returncode != 0:
                err = r.stderr or b""
                low = err.lower()
                if (
                    b"addresssanitizer" in low
                    or b"heap-buffer-overflow" in low
                    or b"stack-buffer-overflow" in low
                    or b"buffer-overflow" in low
                    or b"segmentation fault" in low
                    or b"segfault" in low
                ):
                    return data

            if len(seeds) < 32:
                seeds.append(data)

        return None

    def _randbytes(self, n: int) -> bytes:
        return bytes(random.getrandbits(8) for _ in range(n))

    def _pad_to_target(self, data: bytes, target_min: int = 4000, target_max: int = 8000) -> bytes:
        target = 6180
        if target < target_min:
            target = target_min
        if target > target_max:
            target = target_max
        if len(data) < target:
            data = data + self._randbytes(target - len(data))
        elif len(data) > target_max:
            data = data[:target_max]
        return data

    def _initial_seeds(self) -> list:
        seeds: list[bytes] = []
        seeds.append(b"")
        seeds.append(b"\x00" * 1024)

        s1 = (
            b"\x00\x00\x00\x01\x67"
            + self._randbytes(100)
            + b"\x00\x00\x00\x01\x68"
            + self._randbytes(30)
            + b"\x00\x00\x00\x01\x65"
            + self._randbytes(500)
        )
        seeds.append(self._pad_to_target(s1))

        s2 = (
            b"\x00\x00\x01\x09\xf0"
            + b"\x00\x00\x00\x01\x67"
            + self._randbytes(50)
            + b"\x00\x00\x00\x01\x68"
            + self._randbytes(15)
            + b"\x00\x00\x00\x01\x65"
            + self._randbytes(200)
        )
        seeds.append(self._pad_to_target(s2))

        s3 = (b"\x00\x00\x00\x01" + b"\x65") * 200
        seeds.append(self._pad_to_target(s3))

        seeds.append(self._randbytes(6180))
        return seeds

    def _generate_fresh(self) -> bytes:
        data = bytearray()
        n_nals = random.randint(3, 10)
        for _ in range(n_nals):
            data += b"\x00\x00\x00\x01"
            nal_type = random.choice([1, 5, 7, 8, 9, 14, 15, 20])
            header = ((random.randint(0, 3) << 5) | nal_type) & 0xFF
            data.append(header)
            payload_len = random.randint(10, 600)
            data += self._randbytes(payload_len)
        return self._pad_to_target(bytes(data))

    def _mutate(self, data: bytes) -> bytes:
        if not data:
            return self._generate_fresh()
        b = bytearray(data)
        ops = random.randint(1, 8)
        for _ in range(ops):
            op = random.randint(0, 3)
            if op == 0:
                if not b:
                    continue
                idx = random.randrange(len(b))
                b[idx] = random.getrandbits(8)
            elif op == 1:
                idx = random.randrange(len(b) + 1)
                insert_len = random.randint(1, 32)
                b[idx:idx] = self._randbytes(insert_len)
            elif op == 2:
                if not b:
                    continue
                idx = random.randrange(len(b))
                max_del = min(32, len(b) - idx)
                del_len = random.randint(1, max_del)
                del b[idx : idx + del_len]
            else:
                if not b:
                    continue
                idx = random.randrange(len(b))
                b[idx] ^= 1 << random.randint(0, 7)
        for _ in range(2):
            pos = random.randrange(0, len(b) + 1)
            b[pos:pos] = b"\x00\x00\x00\x01"
            if len(b) > 10000:
                break
        return self._pad_to_target(bytes(b))

    def _fallback_poc(self) -> bytes:
        random.seed(12345)
        data = bytearray()
        while len(data) < 6180:
            data += b"\x00\x00\x00\x01\x67"
            data += self._randbytes(10)
        return bytes(data[:6180])