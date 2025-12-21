import os
import tarfile
import tempfile
import subprocess
import time
import re
import random
import shutil
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        base_temp = tempfile.mkdtemp(prefix="pocgen_")
        try:
            root_dir = self._extract_src(src_path, base_temp)
            binary_path = self._build_and_find_binary(root_dir)
            tokens_info = self._extract_tokens(root_dir)
            static_poc = self._build_static_poc(tokens_info)

            if binary_path and static_poc is not None:
                try:
                    if self._test_input(binary_path, static_poc):
                        return static_poc
                except Exception:
                    pass

            if binary_path:
                try:
                    poc = self._fuzz_for_crash(binary_path, tokens_info, static_poc)
                    if poc is not None:
                        return poc
                except Exception:
                    pass

            if static_poc is not None:
                return static_poc

            return self._default_poc()
        finally:
            try:
                shutil.rmtree(base_temp)
            except Exception:
                pass

    def _extract_src(self, src_path: str, base_temp: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        extract_dir = os.path.join(base_temp, "src")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with tarfile.open(src_path, "r:*") as tar:
                self._safe_extract(tar, path=extract_dir)
        except tarfile.TarError:
            return extract_dir
        entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
        if len(entries) == 1:
            only = os.path.join(extract_dir, entries[0])
            if os.path.isdir(only):
                return only
        return extract_dir

    def _safe_extract(self, tar: tarfile.TarFile, path: str) -> None:
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            if not self._is_within_directory(path, member_path):
                raise Exception("Attempted Path Traversal in Tar File")
        tar.extractall(path)

    def _is_within_directory(self, directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

    def _build_and_find_binary(self, root_dir: str) -> str:
        binary = self._find_binary(root_dir)
        if binary:
            return binary
        self._run_build(root_dir)
        return self._find_binary(root_dir)

    def _run_build(self, root_dir: str) -> None:
        env = os.environ.copy()
        if "CFLAGS" not in env:
            env["CFLAGS"] = "-g -O0"
        if "CXXFLAGS" not in env:
            env["CXXFLAGS"] = "-g -O0"

        scripts = ["build.sh", "build", "compile.sh"]
        for s in scripts:
            path = os.path.join(root_dir, s)
            if os.path.isfile(path):
                try:
                    subprocess.run(
                        ["bash", path],
                        cwd=root_dir,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                    )
                    return
                except Exception:
                    pass

        for mf in ["Makefile", "makefile"]:
            if os.path.isfile(os.path.join(root_dir, mf)):
                try:
                    subprocess.run(
                        ["make", "-j8"],
                        cwd=root_dir,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                    )
                    return
                except Exception:
                    pass

        if os.path.isfile(os.path.join(root_dir, "CMakeLists.txt")):
            build_dir = os.path.join(root_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            try:
                subprocess.run(
                    ["cmake", ".."],
                    cwd=build_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                )
                subprocess.run(
                    ["make", "-j8"],
                    cwd=build_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                )
                return
            except Exception:
                pass

        conf = os.path.join(root_dir, "configure")
        if os.path.isfile(conf) and os.access(conf, os.X_OK):
            try:
                subprocess.run(
                    [conf],
                    cwd=root_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                )
                subprocess.run(
                    ["make", "-j8"],
                    cwd=root_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                )
            except Exception:
                pass

    def _find_binary(self, root_dir: str) -> str:
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            basename = os.path.basename(dirpath)
            if basename in (".git", ".hg", ".svn", "__pycache__", "tests", "test", "doc", "docs"):
                continue
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if not (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext in (
                    ".c",
                    ".cc",
                    ".cpp",
                    ".cxx",
                    ".h",
                    ".hpp",
                    ".py",
                    ".sh",
                    ".txt",
                    ".md",
                    ".json",
                    ".xml",
                    ".yml",
                    ".yaml",
                    ".ini",
                    ".so",
                    ".a",
                    ".dll",
                    ".dylib",
                ):
                    continue
                try:
                    with open(full, "rb") as f:
                        head = f.read(4)
                except OSError:
                    continue
                if head.startswith(b"#!/"):
                    continue
                is_bin = False
                if head.startswith(b"\x7fELF") or head.startswith(b"MZ"):
                    is_bin = True
                if not is_bin and ext in ("", ".out", ".exe"):
                    is_bin = True
                if not is_bin:
                    continue
                rel = os.path.relpath(full, root_dir)
                depth = rel.count(os.sep)
                size = st.st_size
                candidates.append((depth, size, full))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[0][2]

    def _unescape_cpp_string(self, s: str) -> str:
        try:
            bs = s.encode("utf-8", "backslashreplace")
            us = bs.decode("unicode_escape")
        except Exception:
            us = s
        filtered = "".join(ch for ch in us if 9 <= ord(ch) < 127)
        return filtered

    def _extract_tokens(self, root_dir: str) -> dict:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".ipp", ".inc")
        string_literals = set()
        file_texts = {}
        add_context_literals = set()
        node_add_present = False
        re_str = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
        source_files = []

        for dirpath, dirnames, filenames in os.walk(root_dir):
            basename = os.path.basename(dirpath)
            if basename in (".git", ".hg", ".svn", "__pycache__"):
                continue
            for fname in filenames:
                lower = fname.lower()
                if lower.endswith(exts):
                    source_files.append(os.path.join(dirpath, fname))

        add_positions = {}
        for path in source_files:
            try:
                text = open(path, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            file_texts[path] = text
            lines = text.splitlines()
            if "Node::add" in text:
                node_add_present = True
            for i, line in enumerate(lines):
                if "Node::add" in line or ".add(" in line or "->add(" in line:
                    add_positions.setdefault(path, []).append(i)
                for m in re_str.finditer(line):
                    lit = m.group(1)
                    lit = self._unescape_cpp_string(lit)
                    if lit:
                        string_literals.add(lit)

        for path, idx_list in add_positions.items():
            text = file_texts.get(path)
            if text is None:
                continue
            lines = text.splitlines()
            for idx in idx_list:
                start = max(0, idx - 5)
                end = min(len(lines), idx + 6)
                for j in range(start, end):
                    line = lines[j]
                    for m in re_str.finditer(line):
                        lit = m.group(1)
                        lit = self._unescape_cpp_string(lit)
                        if lit:
                            add_context_literals.add(lit)

        keywords = set()
        for s in string_literals:
            if 1 <= len(s) <= 20 and re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-+/]*", s):
                keywords.add(s)

        add_commands = set()
        for s in keywords:
            if "add" in s.lower():
                add_commands.add(s)
        for s in add_context_literals:
            if 1 <= len(s) <= 30 and all(32 <= ord(ch) < 127 for ch in s):
                add_commands.add(s)

        if len(keywords) > 100:
            keywords = set(list(keywords)[:100])
        if len(add_commands) > 20:
            add_commands = set(list(add_commands)[:20])

        return {
            "string_literals": string_literals,
            "keywords": keywords,
            "add_commands": add_commands,
            "node_add_present": node_add_present,
        }

    def _build_static_poc(self, info: dict) -> bytes:
        add_cmds = list(info.get("add_commands") or [])
        keywords = list(info.get("keywords") or [])
        lines = []
        if add_cmds:
            cmds = add_cmds
        else:
            if keywords:
                cmds = keywords
            else:
                cmds = ["add", "ADD", "a"]

        max_repeats = 256
        arg_words = []
        for kw in keywords:
            if len(arg_words) >= 10:
                break
            if kw not in cmds:
                arg_words.append(kw)
        if not arg_words:
            arg_words = ["x", "node", "child", "val"]

        for i in range(max_repeats):
            cmd = cmds[i % len(cmds)]
            arg = arg_words[i % len(arg_words)]
            line = f"{cmd} {arg}{i}\n"
            lines.append(line)

        data = "".join(lines).encode("ascii", "replace")
        if len(data) < 60:
            data += b"A" * (60 - len(data))
        if len(data) > 4096:
            data = data[:4096]
        return data

    def _default_poc(self) -> bytes:
        return b"A" * 60

    def _test_input(self, binary_path: str, data: bytes) -> bool:
        try:
            proc = subprocess.run(
                [binary_path],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2,
            )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        rc = proc.returncode
        stderr = proc.stderr.decode("utf-8", "ignore")
        if rc < 0:
            return True
        if rc != 0:
            lowered = stderr.lower()
            if (
                "addresssanitizer" in lowered
                or "heap-use-after-free" in lowered
                or "use-after-free" in lowered
                or "double free" in lowered
                or "invalid free" in lowered
                or "heap buffer overflow" in lowered
            ):
                return True
            if rc >= 128:
                return True
        return False

    def _fuzz_for_crash(self, binary_path: str, info: dict, static_poc: bytes) -> bytes:
        start = time.time()
        overall_timeout = 40.0

        seeds = []
        seeds.extend(
            [
                b"",
                b"\n",
                b"A",
                b"A" * 4,
                b"A" * 16,
                b"0\n",
                b"1\n",
                b"add\n",
                b"ADD\n",
            ]
        )

        add_cmds = list(info.get("add_commands") or [])
        for cmd in add_cmds:
            try:
                seeds.append((cmd + "\n").encode("ascii", "replace"))
                seeds.append((cmd + " 1\n").encode("ascii", "replace"))
                seeds.append((cmd + " x\n").encode("ascii", "replace"))
            except Exception:
                continue

        keywords = list(info.get("keywords") or [])
        for kw in keywords[:20]:
            try:
                seeds.append((kw + "\n").encode("ascii", "replace"))
            except Exception:
                continue

        if static_poc is not None:
            seeds.append(static_poc)

        seen_inputs = set()
        uniq_seeds = []
        for s in seeds:
            if s not in seen_inputs:
                uniq_seeds.append(s)
                seen_inputs.add(s)
        seeds = uniq_seeds[:100]

        for data in seeds:
            if time.time() - start > overall_timeout:
                return None
            if self._test_input(binary_path, data):
                return data

        corpus = list(seeds)
        max_iterations = 300
        for _ in range(max_iterations):
            if time.time() - start > overall_timeout:
                break
            base = random.choice(corpus)
            mutated = self._mutate_input(base)
            corpus.append(mutated)
            if self._test_input(binary_path, mutated):
                return mutated
        return None

    def _mutate_input(self, data: bytes) -> bytes:
        if not data:
            data = b"A"
        ba = bytearray(data)
        max_len = 1024
        num_ops = random.randint(1, max(1, len(ba) // 4))
        for _ in range(num_ops):
            op = random.randint(0, 2)
            if op == 0 and ba:
                idx = random.randrange(len(ba))
                ba[idx] = random.randint(0, 255)
            elif op == 1 and len(ba) < max_len:
                idx = random.randrange(len(ba) + 1)
                ba.insert(idx, random.randint(0, 255))
            elif op == 2 and ba:
                idx = random.randrange(len(ba))
                del ba[idx]
        if len(ba) > max_len:
            del ba[max_len:]
        return bytes(ba)
