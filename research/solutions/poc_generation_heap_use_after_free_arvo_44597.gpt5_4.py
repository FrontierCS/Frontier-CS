import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = r'''
-- PoC for incorrect code generation when _ENV is declared as <const>
-- This stresses closures that capture a constant _ENV, forces GC,
-- and then exercises the captured environment from outside the scope.

local function allocate_noise(n, sz)
  local t = {}
  for i = 1, n do
    t[i] = string.rep(string.char(65 + (i % 26)), sz)
  end
  return t
end

local function churn()
  local acc = 0
  for i = 1, 200 do
    local t = {}
    for j = 1, 100 do
      t[j] = { j, j * 2, j * 3, str = string.rep("x", j % 50) }
      acc = acc + j
    end
  end
  return acc
end

-- Variation 1: basic maker returning closure that uses global lookup via const _ENV
local function mk1(v)
  do
    local _ENV <const> = { x = v }
    local function g()
      return x + 1
    end
    return g
  end
end

for i = 1, 300 do
  local g = mk1(i)
  collectgarbage("collect")
  local _ = g()
end

-- Variation 2: nested function returning a closure that uses const _ENV
local function mk2(v)
  local f
  do
    local _ENV <const> = { x = v }
    f = function()
      local s = 0
      for i = 1, 50 do
        s = s + x
      end
      return s
    end
  end
  return f
end

for i = 1, 100 do
  local g = mk2(i * 3)
  collectgarbage("collect")
  local _ = g()
end

-- Variation 3: double-nested closures accessing const _ENV
local function mk3(v)
  do
    local _ENV <const> = { x = v }
    local function h()
      local function g()
        return x * 2
      end
      return g
    end
    return h()
  end
end

for i = 1, 120 do
  local g = mk3(i + 7)
  collectgarbage("collect")
  local _ = g()
end

-- Variation 4: use load to compile a chunk that sets const _ENV
local code = [[
  return (function()
    local _ENV <const> = ...
    local function g()
      return x, y, z
    end
    return g
  end)()
]]

for i = 1, 80 do
  local f = assert(load(code))({ x = i, y = i * 2, z = i * 3 })
  collectgarbage("collect")
  local a, b, c = f()
end

-- Variation 5: store closure capturing const _ENV into _G, then call it after GC
do
  local _ENV <const> = { x = 99 }
  _G.fconst = function() return x end
end
collectgarbage("collect"); collectgarbage("collect")
local _ = _G.fconst()

-- Variation 6: heavier environment content to encourage GC and potential miscompilation exposure
local function mk_heavy(idx)
  do
    local _ENV <const> = {
      x = idx,
      bigtable = allocate_noise(50, 200),
      y = idx * 5,
      z = tostring(idx) .. "-" .. string.rep("z", (idx % 30) + 1),
      s = string.rep("S", 100)
    }
    local function g()
      local sum = 0
      for i = 1, 10 do
        sum = sum + x + y
      end
      if bigtable[1] then
        sum = sum + #bigtable[1]
      end
      return sum + #s + #z
    end
    return g
  end
end

for i = 1, 30 do
  local g = mk_heavy(i)
  collectgarbage("collect")
  local _ = g()
end

-- Variation 7: closures leaving scope with multiple globals from const _ENV
local function mk_multi(idx)
  do
    local _ENV <const> = { a = idx, b = idx * 2, c = idx * 3 }
    local function g()
      return a + b + c
    end
    return g
  end
end

for i = 1, 150 do
  local g = mk_multi(i)
  collectgarbage("collect")
  local _ = g()
end

-- Variation 8: mix arithmetic and table access with const _ENV inside for loops
local function mk_loop(idx)
  do
    local _ENV <const> = { base = idx, t = {1,2,3,4,5} }
    local function g()
      local s = base
      for i = 1, #t do
        s = s + t[i]
      end
      return s
    end
    return g
  end
end

for i = 1, 120 do
  local g = mk_loop(i)
  collectgarbage("collect")
  local _ = g()
end

-- Variation 9: Many short-lived closures capturing const _ENV
for i = 1, 500 do
  do
    local _ENV <const> = { x = i }
    local f = function() return x end
    collectgarbage("collect")
    local _ = f()
  end
end

-- Variation 10: Coroutine boundary with const _ENV closure
local function mk_co(idx)
  do
    local _ENV <const> = { x = idx, y = idx + 1 }
    local function g()
      coroutine.yield(x)
      return y
    end
    return g
  end
end

for i = 1, 40 do
  local g = mk_co(i)
  local co = coroutine.create(g)
  local ok, val = coroutine.resume(co)
  if ok then
    local _ = coroutine.resume(co)
  end
  collectgarbage("collect")
end

-- Additional churn and calls to encourage GC cycles between creation and use
for i = 1, 20 do
  churn()
  collectgarbage("collect")
  local g = mk1(i * 11)
  local _ = g()
end
'''
        return poc.encode('utf-8')
