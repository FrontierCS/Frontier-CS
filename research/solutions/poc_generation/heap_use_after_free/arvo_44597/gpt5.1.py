import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        lua_poc = r'''-- PoC for Lua _ENV <const> code generation issue

local candidates = {
[[
-- candidate 1: closure depends only on const _ENV
local function factory1()
  local env = { }
  env.x = { 1 }
  local _ENV <const> = env

  local function inner()
    return x[1]
  end

  env = nil
  collectgarbage("collect")
  return inner
end

local f = factory1()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  f()
end
]],
[[
-- candidate 2: _ENV<const> with local defined after closure
local function factory2()
  local _ENV <const> = _ENV

  local function inner()
    return a[1]
  end

  local a = { 1, 2, 3 }
  return inner
end

local f = factory2()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  f()
end
]],
[[
-- candidate 3: nested block where env is dropped before return
local function factory3()
  local env = { y = { 1 } }
  do
    local _ENV <const> = env
    local function inner()
      return y[1]
    end
    env = nil
    collectgarbage("collect")
    return inner
  end
end

local f = factory3()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  f()
end
]],
[[
-- candidate 4: interaction with another upvalue
local function outer()
  local holder = { 10 }
  local function mk()
    local env = { v = holder }
    local _ENV <const> = env
    local function inner()
      return v, holder
    end
    holder = nil
    env = nil
    collectgarbage("collect")
    return inner
  end
  local f = mk()
  collectgarbage("collect")
  return f
end

local f = outer()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  f()
end
]],
[[
-- candidate 5: several closures share the same const _ENV
local function factory5()
  local env = { z = { 1, 2, 3 } }
  local _ENV <const> = env
  local function a() return z[1] end
  local function b() return z[2] end
  local function c() return z[3] end
  env = nil
  collectgarbage("collect")
  return a, b, c
end

local a, b, c = factory5()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  a(); b(); c()
end
]],
[[
-- candidate 6: coroutine with const _ENV as the only reference to env
local function factory6()
  local env = { k = {} }
  local _ENV <const> = env

  local function work()
    for i = 1, 10 do
      k[i] = i
      coroutine.yield(k)
    end
  end

  env = nil
  collectgarbage("collect")

  local co = coroutine.create(work)
  return co
end

local co = factory6()
collectgarbage("collect")
while coroutine.status(co) ~= "dead" do
  collectgarbage("collect")
  local ok, v = coroutine.resume(co)
end
]],
[[
-- candidate 7: load() a chunk that sets _ENV<const> from varargs
local function driver()
  local env = { g = function() end, val = { 1 } }

  local src =
    "local _ENV <const> = ...\n" ..
    "local function inner()\n" ..
    "  return val[1], g\n" ..
    "end\n" ..
    "collectgarbage('collect')\n" ..
    "return inner\n"

  local loader = assert(load(src, "inner", "t"))
  local inner = loader(env)
  env = nil
  collectgarbage("collect")
  for i = 1, 100 do
    collectgarbage("collect")
    inner()
  end
end

driver()
]],
[[
-- candidate 8: deeply nested functions with const _ENV
local function factory8()
  local env = { t = { 1 } }
  local function layer1()
    local _ENV <const> = env
    local function layer2()
      local function layer3()
        return t[1]
      end
      return layer3
    end
    return layer2()
  end
  local f = layer1()
  env = nil
  collectgarbage("collect")
  return f
end

local f = factory8()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  f()
end
]],
[[
-- candidate 9: function defined before local it closes over, with const _ENV
local function factory9()
  local env = { }
  local _ENV <const> = env
  function use()
    return shared
  end
  local shared = { 42 }
  env = nil
  collectgarbage("collect")
  return use
end

local f = factory9()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  f()
end
]],
[[
-- candidate 10: environment table only reachable through const _ENV
local function factory10()
  local env = { flag = { 1 } }
  local _ENV <const> = env
  local function inner()
    return flag[1]
  end
  env = nil
  collectgarbage("collect")
  return inner
end

local f = factory10()
collectgarbage("collect")
for i = 1, 100 do
  collectgarbage("collect")
  f()
end
]]
}

for i = 1, #candidates do
  local f, err = load(candidates[i], "candidate" .. i, "t")
  if f then
    pcall(f)
  end
end
'''
        return lua_poc.encode('utf-8')