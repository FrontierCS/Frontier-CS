import os
import tarfile
import tempfile
import subprocess
import glob
import random
import time


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_internal(src_path)
        except Exception:
            return b"AAAAAAAA"

    def _solve_internal(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            self._extract_tarball(src_path, tmpdir)
            project_root = self._find_project_root(tmpdir)

            driver_path = None
            # Try with ASan first
            for use_asan in (True, False):
                try:
                    driver_path = self._build_driver(project_root, use_asan=use_asan)
                    if driver_path is not None:
                        break
                except Exception:
                    driver_path = None

            if driver_path is not None:
                poc = self._fuzz_for_crash(driver_path)
                if poc is not None and len(poc) > 0:
                    return poc

        return b"AAAAAAAA"

    def _extract_tarball(self, src_path: str, dst_dir: str) -> None:
        with tarfile.open(src_path, "r:*") as tf:
            tf.extractall(dst_dir)

    def _find_project_root(self, tmpdir: str) -> str:
        entries = [e for e in os.listdir(tmpdir) if not e.startswith(".")]
        root = tmpdir
        if len(entries) == 1:
            candidate = os.path.join(tmpdir, entries[0])
            if os.path.isdir(candidate):
                root = candidate

        cmake_dir = self._find_cmake_dir(root)
        if cmake_dir is not None:
            root = cmake_dir
        return root

    def _find_cmake_dir(self, base: str) -> str | None:
        best_with_header = None
        best_any = None
        for dirpath, dirnames, filenames in os.walk(base):
            if "CMakeLists.txt" in filenames:
                if "pcre2.h" in filenames:
                    if best_with_header is None or len(dirpath) < len(best_with_header):
                        best_with_header = dirpath
                if best_any is None or len(dirpath) < len(best_any):
                    best_any = dirpath
        return best_with_header or best_any

    def _build_driver(self, project_root: str, use_asan: bool) -> str | None:
        build_dir = os.path.join(
            project_root, "aeg_build_asan" if use_asan else "aeg_build"
        )
        os.makedirs(build_dir, exist_ok=True)

        # Configure with CMake
        cmake_cmd = ["cmake", "..", "-DBUILD_SHARED_LIBS=OFF"]
        # These options are specific to PCRE2 but harmless if unused
        cmake_cmd += [
            "-DPCRE2_BUILD_TESTS=OFF",
            "-DPCRE2_BUILD_PCRE2GREP=OFF",
            "-DPCRE2_BUILD_PCRE2TEST=OFF",
        ]

        if use_asan:
            asan_flags = "-fsanitize=address -fno-omit-frame-pointer"
            cmake_cmd.append(f"-DCMAKE_C_FLAGS={asan_flags}")
            cmake_cmd.append("-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address")

        subprocess.run(
            cmake_cmd,
            cwd=build_dir,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
        )

        # Build
        build_cmd = ["cmake", "--build", ".", "-j", str(max(1, os.cpu_count() or 1))]
        subprocess.run(
            build_cmd,
            cwd=build_dir,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
        )

        # Locate PCRE2 library
        libs = sorted(
            glob.glob(os.path.join(build_dir, "**", "libpcre2-8.*"), recursive=True)
        )
        if not libs:
            # Fallback: any libpcre2-8*
            libs = sorted(
                glob.glob(os.path.join(build_dir, "**", "libpcre2-8*"), recursive=True)
            )
        if not libs:
            return None
        lib_path = libs[0]

        driver_c_path = os.path.join(build_dir, "aeg_driver.c")
        self._write_driver_c(driver_c_path)

        driver_path = os.path.join(build_dir, "aeg_driver")
        cc = os.environ.get("CC", "gcc")
        compile_cmd = [cc]
        if use_asan:
            compile_cmd += ["-fsanitize=address", "-fno-omit-frame-pointer"]
        compile_cmd += [
            driver_c_path,
            lib_path,
            "-o",
            driver_path,
            "-I",
            project_root,
            "-I",
            os.path.join(project_root, "src"),
            "-lm",
            "-lpthread",
        ]
        if use_asan:
            compile_cmd.append("-fsanitize=address")

        subprocess.run(
            compile_cmd,
            cwd=build_dir,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
        )

        # Quick sanity run
        try:
            subprocess.run(
                [driver_path],
                input=b"a",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
        except Exception:
            return None

        return driver_path

    def _write_driver_c(self, path: str) -> None:
        code = r'''
#include <stdio.h>
#include <stdlib.h>

#define PCRE2_CODE_UNIT_WIDTH 8
#include "pcre2.h"

int main(void) {
    size_t cap = 1024;
    size_t len = 0;
    unsigned char *buf = (unsigned char *)malloc(cap);
    if (buf == NULL) return 0;

    int ch;
    while ((ch = getchar()) != EOF) {
        if (len == cap) {
            cap *= 2;
            unsigned char *nbuf = (unsigned char *)realloc(buf, cap);
            if (nbuf == NULL) {
                free(buf);
                return 0;
            }
            buf = nbuf;
        }
        buf[len++] = (unsigned char)ch;
    }

    if (len == 0) {
        free(buf);
        return 0;
    }

    int errorcode = 0;
    PCRE2_SIZE erroroffset = 0;
    PCRE2_SPTR pattern = (PCRE2_SPTR)buf;

    pcre2_code *re = pcre2_compile(
        pattern, len, 0, &errorcode, &erroroffset, NULL);
    if (re == NULL) {
        free(buf);
        return 0;
    }

    PCRE2_SPTR subject = (PCRE2_SPTR)buf;
    PCRE2_SIZE subject_length = len;

    /* Make the external ovector definitely larger than the number of
       capturing parentheses in typical patterns. */
    pcre2_match_data *match_data = pcre2_match_data_create(64, NULL);
    if (match_data == NULL) {
        pcre2_code_free(re);
        free(buf);
        return 0;
    }

    (void)pcre2_match(re, subject, subject_length, 0, 0, match_data, NULL);

    pcre2_match_data_free(match_data);
    pcre2_code_free(re);
    free(buf);
    return 0;
}
'''
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

    def _run_input(self, driver_path: str, data: bytes, timeout: float = 0.5) -> bool:
        try:
            result = subprocess.run(
                [driver_path],
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return True
        except Exception:
            return True
        return result.returncode != 0

    def _fuzz_for_crash(self, driver_path: str) -> bytes | None:
        # Deterministic randomness
        random.seed(0)

        seed_patterns = [
            b"()",
            b"(a)",
            b"(a)*",
            b"(a)+",
            b"(a)?",
            b"(a){1,2}",
            b"(ab)",
            b"((a))",
            b"((a)+)",
            b"((a+)+)",
            b"(a(b(c)))",
            b"(.+)",
            b"(.*)",
            b"(a.*)",
            b"(a|b)",
            b"(a(b|c))",
            b"^$",
            b".*",
            b"a*",
            b"a+",
            b"(a*)*",
        ]

        for pat in seed_patterns:
            if self._run_input(driver_path, pat):
                return pat

        alphabet = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.*+?^${}()[]|\\"
        start_time = time.time()
        time_budget = 20.0
        max_iters = 20000

        for _ in range(max_iters):
            if time.time() - start_time > time_budget:
                break
            length = random.randint(1, 32)
            data = bytes(random.choice(alphabet) for _ in range(length))
            if self._run_input(driver_path, data):
                return data

        return None