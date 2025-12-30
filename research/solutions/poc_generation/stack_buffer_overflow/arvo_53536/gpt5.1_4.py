import os
import tarfile
import tempfile
import subprocess
import re
import shutil
import random
from typing import List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_impl(src_path)
        except Exception:
            return self._fallback_poc()

    def _solve_impl(self, src_path: str) -> bytes:
        random.seed(0)
        with tempfile.TemporaryDirectory() as tmpdir:
            self._extract_tarball(src_path, tmpdir)
            project_root = self._detect_project_root(tmpdir)
            source_files, is_cpp = self._collect_source_files(project_root)
            if not source_files:
                return self._fallback_poc()

            prog_path = self._compile_with_asan(project_root, source_files, is_cpp)
            if prog_path is None:
                return self._fallback_poc()

            tokens = self._find_candidate_tokens(source_files)
            candidate_inputs = self._build_candidate_inputs(tokens)

            for data in candidate_inputs:
                if self._run_and_check(prog_path, data):
                    return data

            return self._fallback_poc()

    def _extract_tarball(self, src_path: str, dst_dir: str) -> None:
        if os.path.isdir(src_path):
            # If it's already a directory, copy contents
            for item in os.listdir(src_path):
                s = os.path.join(src_path, item)
                d = os.path.join(dst_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(dst_dir)
        except tarfile.ReadError:
            # Not a tarball; try to treat as single file directory-less project
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src_path, os.path.join(dst_dir, os.path.basename(src_path)))

    def _detect_project_root(self, base_dir: str) -> str:
        try:
            entries = [os.path.join(base_dir, e) for e in os.listdir(base_dir)]
        except FileNotFoundError:
            return base_dir
        dirs = [e for e in entries if os.path.isdir(e)]
        if len(dirs) == 1 and len(entries) == 1:
            return dirs[0]
        return base_dir

    def _collect_source_files(self, root: str) -> Tuple[List[str], bool]:
        c_files: List[str] = []
        cpp_files: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip hidden directories
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fname in filenames:
                if fname.startswith("."):
                    continue
                path = os.path.join(dirpath, fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext == ".c":
                    c_files.append(path)
                elif ext in (".cpp", ".cc", ".cxx"):
                    cpp_files.append(path)
        if cpp_files:
            return cpp_files + c_files, True
        return c_files, False

    def _find_compiler(self, is_cpp: bool) -> str:
        if is_cpp:
            candidates = ["clang++", "g++"]
        else:
            candidates = ["clang", "gcc"]
        for c in candidates:
            if shutil.which(c):
                return c
        return ""

    def _compile_with_asan(self, root: str, sources: List[str], is_cpp: bool) -> str:
        compiler = self._find_compiler(is_cpp)
        if not compiler:
            return None

        main_candidates = self._find_main_sources(sources)
        if not main_candidates:
            main_candidates = sources[:1]

        prog_path = os.path.join(root, "poc_target")
        std_flag = "-std=c++11" if is_cpp else "-std=c11"

        # First try: all sources
        cmd = [
            compiler,
            std_flag,
            "-fsanitize=address",
            "-g",
            "-O1",
            "-Wall",
            "-Wextra",
            "-Wno-unused-parameter",
            "-Wno-unused-variable",
            "-o",
            prog_path,
        ] + sources

        if self._run_compile(cmd, root):
            return prog_path

        # Second try: all sources + -lm
        cmd_lm = cmd[:-len(sources)] + ["-lm"] + sources
        if self._run_compile(cmd_lm, root):
            return prog_path

        # Third try: only main file
        main_file = main_candidates[0]
        cmd_main = [
            compiler,
            std_flag,
            "-fsanitize=address",
            "-g",
            "-O1",
            "-Wall",
            "-Wextra",
            "-Wno-unused-parameter",
            "-Wno-unused-variable",
            "-o",
            prog_path,
            main_file,
        ]
        if self._run_compile(cmd_main, root):
            return prog_path

        # Fourth try: only main file + -lm
        cmd_main_lm = cmd_main[:-1] + ["-lm", main_file]
        if self._run_compile(cmd_main_lm, root):
            return prog_path

        return None

    def _run_compile(self, cmd: List[str], cwd: str) -> bool:
        try:
            res = subprocess.run(
                cmd,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _find_main_sources(self, sources: List[str]) -> List[str]:
        main_files: List[Tuple[int, str]] = []
        pattern = re.compile(r"\bmain\s*\(")
        for path in sources:
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            if pattern.search(content):
                depth = path.count(os.sep)
                main_files.append((depth, path))
        main_files.sort()
        return [p for _, p in main_files]

    def _unescape_c_string(self, s: str) -> str:
        result_chars: List[str] = []
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c != "\\":
                result_chars.append(c)
                i += 1
            else:
                i += 1
                if i >= n:
                    break
                esc = s[i]
                i += 1
                if esc == "n":
                    result_chars.append("\n")
                elif esc == "t":
                    result_chars.append("\t")
                elif esc == "r":
                    result_chars.append("\r")
                elif esc == "0":
                    result_chars.append("\0")
                elif esc == "x":
                    # hex sequence (up to 2 hex digits)
                    j = i
                    hex_digits = []
                    while j < n and s[j] in "0123456789abcdefABCDEF" and len(hex_digits) < 2:
                        hex_digits.append(s[j])
                        j += 1
                    if hex_digits:
                        try:
                            val = int("".join(hex_digits), 16)
                            result_chars.append(chr(val))
                        except ValueError:
                            pass
                        i = j
                    else:
                        result_chars.append("x")
                else:
                    # simple escape such as \" or \\
                    result_chars.append(esc)
        return "".join(result_chars)

    def _unescape_c_char(self, s: str) -> str:
        # s contains the inner of a char literal, e.g. "a" or "\\n"
        unescaped = self._unescape_c_string(s)
        return unescaped[0] if unescaped else ""

    def _find_candidate_tokens(self, source_files: List[str]) -> List[str]:
        tokens: List[str] = []
        token_set = set()
        special_chars = "<>[]{}%$#@!/&?:"
        # String literals based tokens
        for path in source_files:
            try:
                with open(path, "r", errors="ignore") as f:
                    text = f.read()
            except Exception:
                continue
            for m in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text):
                raw = m.group(1)
                lit = self._unescape_c_string(raw)
                if not lit:
                    continue
                if len(lit) > 16:
                    continue
                if not any(ch in lit for ch in special_chars):
                    continue
                if lit in token_set:
                    continue
                token_set.add(lit)
                tokens.append(lit)
                if len(tokens) >= 20:
                    break
            if len(tokens) >= 20:
                break

        # Char literals containing special chars
        char_set = set()
        for path in source_files:
            try:
                with open(path, "r", errors="ignore") as f:
                    text = f.read()
            except Exception:
                continue
            for m in re.finditer(r"'([^'\\]|\\.)'", text):
                inner = m.group(1)
                ch = self._unescape_c_char(inner)
                if ch and ch in special_chars and ch not in char_set:
                    char_set.add(ch)
            if len(char_set) >= 10:
                break

        for ch in char_set:
            if ch not in token_set:
                token_set.add(ch)
                tokens.append(ch)

        # Generic fallback tokens that often represent "tags"
        generic_tokens = [
            "<tag>",
            "</tag>",
            "<TAG>",
            "</TAG>",
            "<b>",
            "</b>",
            "<i>",
            "</i>",
            "<>",
            "[]",
            "{}",
            "%s",
            "%d",
            "%x",
            "%s%",
            "%d%",
            "%x%",
            "${}",
            "$var$",
            "@@",
            "##",
            "{{}}",
            "[[]]",
            "<!-- -->",
        ]
        single_specials = list("<>[]{}%$#@!/&?")
        for t in generic_tokens + single_specials:
            if t not in token_set:
                token_set.add(t)
                tokens.append(t)

        return tokens

    def _build_candidate_inputs(self, tokens: List[str]) -> List[bytes]:
        inputs: List[bytes] = []
        lengths = [256, 512, 1024, 1536, 2048]
        max_len = 5000

        # Plain large buffers without tags
        for L in lengths:
            inputs.append(b"A" * L)
            inputs.append(b"B" * L)

        # Inputs based on individual tokens
        for tok in tokens:
            try:
                tok_bytes = tok.encode("utf-8", errors="ignore")
            except Exception:
                continue
            if not tok_bytes:
                continue
            for L in lengths:
                reps = max(1, L // max(1, len(tok_bytes)))
                data = tok_bytes * reps
                if len(data) > max_len:
                    data = data[:max_len]
                inputs.append(data)
                # Surrounded by filler
                prefix = b"A" * (L // 4)
                suffix = b"B" * (L // 4)
                data2 = prefix + data + suffix
                if len(data2) > max_len:
                    data2 = data2[:max_len]
                inputs.append(data2)

        # Combined tokens sequences
        if tokens:
            random.seed(0)
            limited_tokens = tokens[:20]
            for L in lengths:
                s = bytearray()
                while len(s) < L:
                    tok = random.choice(limited_tokens)
                    try:
                        tb = tok.encode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    if not tb:
                        continue
                    s.extend(tb)
                if len(s) > max_len:
                    s = s[:max_len]
                inputs.append(bytes(s))

        # Nested tag-like patterns if we have any '<'
        has_angle = any(t.startswith("<") for t in tokens)
        if has_angle:
            open_tag = None
            close_tag = None
            for t in tokens:
                if t.startswith("<") and not t.startswith("</"):
                    open_tag = t
                    break
            for t in tokens:
                if t.startswith("</"):
                    close_tag = t
                    break
            if open_tag is None:
                open_tag = "<TAG>"
            if close_tag is None:
                close_tag = "</TAG>"
            pattern = open_tag + "AAAA" + close_tag
            try:
                pattern_bytes = pattern.encode("utf-8", errors="ignore")
            except Exception:
                pattern_bytes = b"<TAG>AAAA</TAG>"
            data = pattern_bytes * 200
            if len(data) > max_len:
                data = data[:max_len]
            inputs.append(data)

        # Ensure uniqueness and reasonable sizes
        unique_inputs: List[bytes] = []
        seen = set()
        for data in inputs:
            if not data:
                continue
            if len(data) > max_len:
                data = data[:max_len]
            if data in seen:
                continue
            seen.add(data)
            unique_inputs.append(data)

        # As a last-resort candidate, very large mixture of various tokens
        if tokens:
            big = bytearray()
            for i in range(1000):
                tok = tokens[i % len(tokens)]
                try:
                    tb = tok.encode("utf-8", errors="ignore")
                except Exception:
                    continue
                big.extend(tb)
                if len(big) >= max_len:
                    break
            big_bytes = bytes(big[:max_len])
            if big_bytes and big_bytes not in seen:
                unique_inputs.append(big_bytes)

        return unique_inputs

    def _run_and_check(self, prog_path: str, data: bytes) -> bool:
        tmpdir = os.path.dirname(prog_path) or "."
        in_path = os.path.join(tmpdir, "input.bin")
        try:
            with open(in_path, "wb") as f:
                f.write(data)
        except Exception:
            return False

        try:
            res = subprocess.run(
                [prog_path, in_path],
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=1.0,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        if res.returncode == 0:
            return False

        try:
            err = res.stderr.decode("utf-8", errors="ignore")
        except Exception:
            return False

        if "AddressSanitizer" in err and "stack-buffer-overflow" in err:
            return True
        return False

    def _fallback_poc(self) -> bytes:
        # Generic fallback: many <TAG> patterns to try to trigger tag-related overflow.
        target_len = 1461
        pattern = b"<TAG>"
        reps = target_len // len(pattern) + 2
        data = pattern * reps
        if len(data) > target_len:
            data = data[:target_len]
        elif len(data) < target_len:
            data += b"A" * (target_len - len(data))
        return data