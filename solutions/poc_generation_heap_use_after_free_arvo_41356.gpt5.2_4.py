import os
import re
import io
import math
import tarfile
import tempfile
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Callable


def _is_within_directory(directory: str, target: str) -> bool:
    directory = os.path.abspath(directory)
    target = os.path.abspath(target)
    try:
        common = os.path.commonpath([directory, target])
    except Exception:
        return False
    return common == directory


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if m.islnk() or m.issym():
                continue
            out_path = os.path.join(dst_dir, m.name)
            if not _is_within_directory(dst_dir, out_path):
                continue
        tf.extractall(dst_dir)


def _read_text_file(path: str, limit_bytes: int = 2_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(limit_bytes)
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")
    except Exception:
        return ""


def _walk_files(root: str, exts: Tuple[str, ...]) -> List[str]:
    out = []
    for dp, dn, fn in os.walk(root):
        for n in fn:
            ln = n.lower()
            if any(ln.endswith(e) for e in exts):
                out.append(os.path.join(dp, n))
    return out


def _find_project_root(extracted_base: str) -> str:
    # Prefer directory containing CMakeLists.txt or Makefile with many sources.
    dirs = set()
    for dp, dn, fn in os.walk(extracted_base):
        if "CMakeLists.txt" in fn or "Makefile" in fn or "makefile" in fn:
            dirs.add(dp)

    cpp_exts = (".cpp", ".cc", ".cxx", ".c", ".hpp", ".hh", ".hxx", ".h")
    if not dirs:
        # if single top-level dir exists, prefer it
        top_entries = [os.path.join(extracted_base, x) for x in os.listdir(extracted_base)]
        top_dirs = [p for p in top_entries if os.path.isdir(p)]
        if len(top_dirs) == 1:
            return top_dirs[0]
        return extracted_base

    best = None
    best_score = -1
    for d in dirs:
        src_count = len(_walk_files(d, cpp_exts))
        depth = os.path.abspath(d).count(os.sep)
        score = src_count * 1000 - depth
        if score > best_score:
            best_score = score
            best = d
    return best if best else extracted_base


def _find_main_candidates(cpp_files: List[str]) -> List[str]:
    mains = []
    main_re = re.compile(r'\b(?:int|auto)\s+main\s*\(', re.M)
    for p in cpp_files:
        txt = _read_text_file(p)
        if main_re.search(txt):
            mains.append(p)
    # Prefer non-test paths
    def key(p: str) -> Tuple[int, int, int, str]:
        lp = p.lower()
        is_test = 1 if any(x in lp for x in ("/test", "\\test", "/tests", "\\tests", "/fuzz", "\\fuzz", "/bench", "\\bench", "/example", "\\example")) else 0
        depth = os.path.abspath(p).count(os.sep)
        size = 0
        try:
            size = os.path.getsize(p)
        except Exception:
            pass
        return (is_test, depth, -size, p)
    mains.sort(key=key)
    return mains


def _gather_include_dirs(root: str) -> List[str]:
    # include root + directories that contain headers
    hdr_exts = (".h", ".hpp", ".hh", ".hxx")
    dirs = {root}
    for dp, dn, fn in os.walk(root):
        if any(n.lower().endswith(hdr_exts) for n in fn):
            dirs.add(dp)
    # stable ordering: root first then sorted by depth/lex
    dirs_list = list(dirs)
    dirs_list.sort(key=lambda d: (0 if os.path.abspath(d) == os.path.abspath(root) else 1, os.path.abspath(d).count(os.sep), d))
    return dirs_list


def _source_hints(root: str) -> Dict[str, object]:
    cpp_files = _walk_files(root, (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"))
    all_text = []
    for p in cpp_files[:200]:
        all_text.append(_read_text_file(p))
    blob = "\n".join(all_text)

    hints = {}
    low = blob.lower()
    hints["json"] = ("json" in low) or ("rapidjson" in low) or ("nlohmann" in low)
    hints["yaml"] = ("yaml" in low)
    hints["xml"] = ("xml" in low) or ("tinyxml" in low)
    hints["ini"] = ("ini" in low)
    hints["stdin"] = ("std::cin" in blob) or ("getline(std::cin" in low)
    hints["fread"] = ("fread" in low) or ("read(" in low) or ("ifstream" in low) or ("fopen" in low)

    # Extract likely command keywords
    str_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
    strings = []
    for m in str_re.finditer(blob):
        s = m.group(1)
        if len(s) == 0 or len(s) > 24:
            continue
        if any(ch in s for ch in ("\n", "\r", "\t")):
            continue
        if not all(32 <= ord(c) < 127 for c in s):
            continue
        strings.append(s)

    # Focus on potential command words
    cmd_words = set()
    for s in strings:
        sl = s.lower()
        if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_\-]{1,16}", s) is None:
            continue
        if any(k in sl for k in ("add", "insert", "node", "push", "append", "set", "put", "create")):
            cmd_words.add(s)
        if sl in ("add", "insert", "set", "put", "node", "new", "create"):
            cmd_words.add(s)
    hints["cmd_words"] = sorted(cmd_words, key=lambda x: (len(x), x.lower()))

    # Infer magic strings (uppercase/alnum) used in comparisons
    magic = set()
    for s in strings:
        if 2 <= len(s) <= 8 and re.fullmatch(r"[A-Z0-9]{2,8}", s):
            magic.add(s)
    hints["magic"] = sorted(magic, key=lambda x: (-len(x), x))

    # Infer possible flags
    flags = set()
    for s in strings:
        if re.fullmatch(r"--[a-zA-Z0-9][a-zA-Z0-9_\-]{1,20}", s):
            flags.add(s)
        if re.fullmatch(r"-[a-zA-Z]", s):
            flags.add(s)
    # prioritize file/input flags
    prioritized = []
    for f in flags:
        fl = f.lower()
        if any(k in fl for k in ("file", "input", "in", "src")):
            prioritized.append(f)
    prioritized.sort(key=lambda x: (len(x), x))
    hints["flags"] = prioritized[:12]

    return hints


def _extract_node_add_throw_messages(root: str) -> List[str]:
    cpp_files = _walk_files(root, (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"))
    needle = re.compile(r"\bNode\s*::\s*add\s*\(", re.M)
    throw_msgs = []
    for p in cpp_files:
        txt = _read_text_file(p)
        m = needle.search(txt)
        if not m:
            continue
        # Extract function body roughly by brace matching starting from first '{' after match
        start = txt.find("{", m.end())
        if start == -1:
            continue
        depth = 0
        end = None
        for i in range(start, len(txt)):
            c = txt[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            continue
        body = txt[start:end]
        for tm in re.finditer(r"\bthrow\b[^;]*;", body, re.S):
            seg = tm.group(0)
            for sm in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', seg):
                s = sm.group(1)
                if 0 < len(s) <= 80:
                    throw_msgs.append(s)
        if throw_msgs:
            break
    return throw_msgs


@dataclass
class _Runner:
    exe_path: str
    arg_templates: List[Tuple[str, ...]]
    timeout_s: float = 2.0

    def run(self, payload: bytes, use_file: bool, args_tpl: Tuple[str, ...]) -> Tuple[int, bytes, bytes, bool]:
        env = os.environ.copy()
        env.setdefault("ASAN_OPTIONS", "abort_on_error=1:detect_leaks=0:allocator_may_return_null=1")
        env.setdefault("UBSAN_OPTIONS", "halt_on_error=1:abort_on_error=1:print_stacktrace=1")

        try:
            if use_file:
                with tempfile.NamedTemporaryFile(prefix="poc_", delete=False) as tf:
                    tf.write(payload)
                    tf.flush()
                    pth = tf.name
                args = [self.exe_path] + [a if a != "{file}" else pth for a in args_tpl]
                try:
                    cp = subprocess.run(
                        args,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=self.timeout_s,
                        env=env,
                    )
                    return cp.returncode, cp.stdout, cp.stderr, False
                finally:
                    try:
                        os.unlink(pth)
                    except Exception:
                        pass
            else:
                args = [self.exe_path] + [a for a in args_tpl if a != "{file}"]
                cp = subprocess.run(
                    args,
                    input=payload,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout_s,
                    env=env,
                )
                return cp.returncode, cp.stdout, cp.stderr, False
        except subprocess.TimeoutExpired as te:
            out = te.stdout if te.stdout is not None else b""
            err = te.stderr if te.stderr is not None else b""
            return 124, out, err, True
        except Exception as e:
            return 125, b"", (str(e).encode("utf-8", errors="ignore")), False


def _is_sanitizer_uaf_or_double_free(stderr: bytes) -> bool:
    if not stderr:
        return False
    s = stderr.lower()
    keys = (
        b"addresssanitizer",
        b"heap-use-after-free",
        b"use-after-free",
        b"double free",
        b"attempting double-free",
        b"invalid free",
        b"asan",
    )
    if any(k in s for k in keys):
        # Avoid matching generic asan without error; still fine because AddressSanitizer usually prints on error
        if b"error:" in s or b"==error:" in s or b"runtime error" in s or b"heap-use-after-free" in s or b"double" in s or b"invalid free" in s:
            return True
        # Some asan versions don't include "ERROR:" in lowercased stderr segments; accept.
        return True
    return False


def _manual_build(root: str, build_dir: str) -> Optional[str]:
    cpp_files = _walk_files(root, (".cpp", ".cc", ".cxx"))
    if not cpp_files:
        return None
    main_files = _find_main_candidates(cpp_files)
    if not main_files:
        return None
    chosen_main = main_files[0]
    other_sources = []
    main_set = set(main_files)
    for p in cpp_files:
        if p in main_set:
            continue
        other_sources.append(p)
    # If no other sources, just compile main
    sources = [chosen_main] + other_sources

    include_dirs = _gather_include_dirs(root)
    inc_args = []
    for d in include_dirs:
        inc_args.extend(["-I", d])

    exe_path = os.path.join(build_dir, "prog_asan")
    cmd = ["g++", "-std=c++17", "-O1", "-g", "-fno-omit-frame-pointer",
           "-fsanitize=address", "-fno-sanitize-recover=address",
           "-D_GLIBCXX_ASSERTIONS", "-Wno-deprecated-declarations"] + inc_args + sources + ["-o", exe_path]
    try:
        cp = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if cp.returncode != 0:
            # try -std=c++14
            cmd2 = ["g++", "-std=c++14", "-O1", "-g", "-fno-omit-frame-pointer",
                    "-fsanitize=address", "-fno-sanitize-recover=address",
                    "-D_GLIBCXX_ASSERTIONS", "-Wno-deprecated-declarations"] + inc_args + sources + ["-o", exe_path]
            cp2 = subprocess.run(cmd2, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            if cp2.returncode != 0:
                return None
        if os.path.exists(exe_path) and os.access(exe_path, os.X_OK):
            return exe_path
    except Exception:
        return None
    return None


def _cmake_build(root: str, build_dir: str) -> List[str]:
    cmakelists = os.path.join(root, "CMakeLists.txt")
    if not os.path.exists(cmakelists):
        return []
    exes = []
    try:
        os.makedirs(build_dir, exist_ok=True)
        env = os.environ.copy()
        env["CXXFLAGS"] = env.get("CXXFLAGS", "") + " -O1 -g -fno-omit-frame-pointer -fsanitize=address -fno-sanitize-recover=address"
        env["CFLAGS"] = env.get("CFLAGS", "") + " -O1 -g -fno-omit-frame-pointer -fsanitize=address -fno-sanitize-recover=address"
        cfg = ["cmake", "-S", root, "-B", build_dir, "-DCMAKE_BUILD_TYPE=RelWithDebInfo"]
        cp = subprocess.run(cfg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, env=env)
        if cp.returncode != 0:
            return []
        bld = ["cmake", "--build", build_dir, "-j", str(min(8, os.cpu_count() or 2))]
        cp2 = subprocess.run(bld, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, env=env)
        if cp2.returncode != 0:
            return []
        # find executables in build dir
        for dp, dn, fn in os.walk(build_dir):
            if "CMakeFiles" in dp:
                continue
            for n in fn:
                p = os.path.join(dp, n)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 200 * 1024 * 1024:
                    continue
                if not os.path.isfile(p):
                    continue
                if not os.access(p, os.X_OK):
                    continue
                ln = n.lower()
                if ln.endswith((".a", ".so", ".o", ".obj", ".dll", ".dylib")):
                    continue
                exes.append(p)
    except Exception:
        return []
    # De-dup & rank: prefer paths containing "bin" or "src"
    exes = sorted(set(exes), key=lambda p: (0 if any(k in p.lower() for k in ("/bin/", "\\bin\\", "/src/", "\\src\\")) else 1, len(p), p))
    return exes[:12]


def _infer_arg_templates(hints: Dict[str, object]) -> List[Tuple[str, ...]]:
    tmpls: List[Tuple[str, ...]] = []
    # no args, stdin
    tmpls.append(tuple())
    # file as first arg
    tmpls.append(("{file}",))
    flags = hints.get("flags") or []
    for f in flags:
        tmpls.append((f, "{file}"))
    # some common flags
    for f in ("-i", "--input", "-f", "--file"):
        tmpls.append((f, "{file}"))
    # de-dup preserving order
    seen = set()
    out = []
    for t in tmpls:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _generate_candidates(hints: Dict[str, object], throw_msgs: List[str]) -> List[bytes]:
    candidates: List[bytes] = []

    msg_blob = " ".join(throw_msgs).lower()
    likely_duplicate = any(k in msg_blob for k in ("duplicate", "already", "exists", "present", "redefined", "redefinition"))
    likely_too_many = any(k in msg_blob for k in ("too many", "maximum", "max", "capacity", "limit"))

    cmd_words = hints.get("cmd_words") or []
    cmd_variants = []
    for w in cmd_words:
        wl = w.lower()
        if wl in ("add", "insert", "set", "put", "create", "node", "append", "push"):
            cmd_variants.append(w)
    # Add common if nothing found
    for w in ("add", "ADD", "insert", "INSERT", "set", "SET", "put", "PUT", "node", "NODE", "create", "CREATE"):
        if w not in cmd_variants:
            cmd_variants.append(w)

    def add_text(s: str):
        candidates.append(s.encode("utf-8", errors="ignore"))

    # Binary-ish candidates with magic prefixes
    for m in (hints.get("magic") or [])[:8]:
        try:
            b = m.encode("ascii", errors="ignore")
        except Exception:
            continue
        candidates.append(b + b"\x00" * 32)
        candidates.append(b + b"\x01" * 16 + b"\x00" * 16)

    # Format hints ordering
    if hints.get("json"):
        add_text('{"a":1,"a":2}\n')
        add_text('{"":0,"":1}\n')
        add_text('{"k":{"a":1},"k":2}\n')
        add_text('{"a":[1,2,3],"a":[4]}\n')
    if hints.get("yaml"):
        add_text("a: 1\na: 2\n")
        add_text("k:\n  a: 1\nk: 2\n")
    if hints.get("ini"):
        add_text("[s]\na=1\na=2\n")
        add_text("a=1\na=2\n")
    if hints.get("xml"):
        add_text("<a><b></b><b></b></a>\n")
        add_text("<r><n id='1'/><n id='1'/></r>\n")

    # Generic duplicates for key/value or token streams
    add_text("a=1\na=2\n")
    add_text("a 1\na 2\n")
    add_text("1 1\n1 1\n")
    add_text("a:1\na:2\n")
    add_text("a\n" * 2)

    # Command-oriented patterns
    for cmd in cmd_variants[:12]:
        if likely_too_many and not likely_duplicate:
            add_text(f"{cmd} a\n{cmd} b\n{cmd} c\n")
            add_text(f"{cmd} 1\n{cmd} 2\n{cmd} 3\n")
        # duplicates
        add_text(f"{cmd} a\n{cmd} a\n")
        add_text(f"{cmd} 1\n{cmd} 1\n")
        add_text(f"{cmd} a 1\n{cmd} a 2\n")
        add_text(f"{cmd} a a\n{cmd} a a\n")

    # Structured bracketed candidates (generic AST-like)
    if likely_duplicate or not likely_too_many:
        add_text('{"x":0,"x":0}\n')
        add_text("(add a)(add a)\n")
        add_text("(a (b) (b))\n")
        add_text("a{b;b}\n")
        add_text("a(b,b)\n")
    else:
        add_text("(op 1 2 3)\n")
        add_text("op(1,2,3)\n")
        add_text("{a,b,c}\n")

    # De-dup and keep reasonable sizes
    out = []
    seen = set()
    for c in candidates:
        if not c:
            continue
        if len(c) > 4096:
            continue
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    # Prioritize smaller first (shorter PoCs)
    out.sort(key=lambda b: (len(b), b[:32]))
    return out


def _ddmin(payload: bytes, check: Callable[[bytes], bool], max_checks: int = 250) -> bytes:
    if not payload:
        return payload
    if not check(payload):
        return payload

    checks = 0
    cur = payload
    n = 2
    cache: Dict[bytes, bool] = {}

    def cached_check(p: bytes) -> bool:
        nonlocal checks
        if p in cache:
            return cache[p]
        if checks >= max_checks:
            cache[p] = False
            return False
        checks += 1
        r = check(p)
        cache[p] = r
        return r

    while len(cur) >= 2 and checks < max_checks:
        length = len(cur)
        chunk = int(math.ceil(length / n))
        reduced = False
        for i in range(n):
            start = i * chunk
            end = min(length, (i + 1) * chunk)
            if start >= end:
                continue
            trial = cur[:start] + cur[end:]
            if trial == cur or len(trial) == 0:
                continue
            if cached_check(trial):
                cur = trial
                n = max(2, n - 1)
                reduced = True
                break
        if not reduced:
            if n >= length:
                break
            n = min(length, n * 2)
    return cur


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Baseline fallback
        fallback = b'{"a":1,"a":2}\n'

        with tempfile.TemporaryDirectory(prefix="arvo_src_") as td:
            try:
                _safe_extract_tar(src_path, td)
            except Exception:
                return fallback

            root = _find_project_root(td)
            hints = _source_hints(root)
            throw_msgs = _extract_node_add_throw_messages(root)
            candidates = _generate_candidates(hints, throw_msgs)

            # Try to build an instrumented binary to validate candidates and minimize
            exes: List[str] = []
            with tempfile.TemporaryDirectory(prefix="arvo_build_") as bd:
                exe_manual = _manual_build(root, bd)
                if exe_manual:
                    exes = [exe_manual]
                else:
                    exes = _cmake_build(root, os.path.join(bd, "cmake_build"))

                if not exes:
                    # No local validation possible; return best guess based on hints
                    if hints.get("json"):
                        return b'{"a":1,"a":2}\n'
                    if hints.get("yaml"):
                        return b"a: 1\na: 2\n"
                    if hints.get("xml"):
                        return b"<a><b></b><b></b></a>\n"
                    return fallback

                arg_templates = _infer_arg_templates(hints)

                found: Optional[Tuple[_Runner, bool, Tuple[str, ...], bytes]] = None

                for exe in exes:
                    runner = _Runner(exe_path=exe, arg_templates=arg_templates, timeout_s=2.0)
                    for c in candidates[:80]:
                        for tpl in arg_templates:
                            # Decide stdin/file based on presence of {file}
                            use_file = "{file}" in tpl
                            rc, out, err, to = runner.run(c, use_file=use_file, args_tpl=tpl)
                            if to:
                                continue
                            if rc != 0 and _is_sanitizer_uaf_or_double_free(err):
                                found = (runner, use_file, tpl, c)
                                break
                        if found:
                            break
                    if found:
                        break

                if not found:
                    # If we didn't trigger, return a robust duplicate-ish text payload
                    # Slightly larger but generic
                    return b'{"a":1,"a":2,"b":3,"c":4,"d":{"x":1,"x":2}}\n'

                runner, use_file, tpl, seed = found

                cache: Dict[bytes, bool] = {}

                def check(p: bytes) -> bool:
                    if p in cache:
                        return cache[p]
                    rc, out, err, to = runner.run(p, use_file=use_file, args_tpl=tpl)
                    ok = (not to) and (rc != 0) and _is_sanitizer_uaf_or_double_free(err)
                    cache[p] = ok
                    return ok

                minimized = _ddmin(seed, check, max_checks=220)
                if minimized:
                    return minimized
                return seed if seed else fallback