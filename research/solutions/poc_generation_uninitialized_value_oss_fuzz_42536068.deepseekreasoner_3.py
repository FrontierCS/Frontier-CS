import os
import tarfile
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source to understand vulnerability context
        # Look for patterns that might indicate file format or parsing logic
        with tarfile.open(src_path, 'r:*') as tar:
            with tempfile.TemporaryDirectory() as tmpdir:
                tar.extractall(tmpdir)
                
                # Look for common file format indicators
                format_hints = self._analyze_source(tmpdir)
                
                # Generate PoC based on analysis
                if format_hints.get('is_binary', False):
                    return self._generate_binary_poc(format_hints)
                else:
                    return self._generate_text_poc(format_hints)
    
    def _analyze_source(self, root_dir):
        """Analyze extracted source for format hints."""
        hints = {
            'is_binary': False,
            'magic_bytes': set(),
            'file_extensions': set(),
            'keywords': set()
        }
        
        # Walk through source files
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.h', '.hpp')):
                    try:
                        with open(os.path.join(root, file), 'r', errors='ignore') as f:
                            content = f.read()
                            # Look for file format indicators
                            if 'fread' in content or 'fwrite' in content:
                                hints['is_binary'] = True
                            if 'magic' in content.lower():
                                hints['keywords'].add('magic')
                            if 'header' in content.lower():
                                hints['keywords'].add('header')
                            if 'parse' in content.lower():
                                hints['keywords'].add('parse')
                            if 'attribute' in content.lower():
                                hints['keywords'].add('attribute')
                            if 'conversion' in content.lower():
                                hints['keywords'].add('conversion')
                    except:
                        continue
                elif not file.endswith(('.py', '.txt', '.md', '.rst')):
                    hints['file_extensions'].add(os.path.splitext(file)[1])
        
        return hints
    
    def _generate_binary_poc(self, hints):
        """Generate binary PoC that might trigger uninitialized value."""
        # Create a binary file with:
        # 1. Valid header to pass initial checks
        # 2. Malformed structure to cause failed conversions
        # 3. Uninitialized data regions
        
        # Start with some common magic bytes
        if 'magic' in hints['keywords']:
            poc = b'\x89PNG\r\n\x1a\n'  # PNG header
            poc += b'\x00\x00\x00\x0dIHDR'  # Chunk header
        else:
            poc = b'\xff\xd8\xff\xe0'  # JPEG header
            poc += b'\x00\x10JFIF\x00\x01\x02'
        
        # Add malformed attribute section
        # This might cause conversion failures without errors
        poc += b'\x01'  # Attribute count
        
        # Invalid attribute type that might fail conversion
        poc += b'\xff'  # Invalid type marker
        
        # Uninitialized data region - values that weren't properly set
        # Size: target 2179 bytes total
        current_len = len(poc)
        uninit_size = 2179 - current_len - 4
        
        # Add uninitialized-looking data (mix of zeros and garbage)
        uninit_data = b'\x00' * (uninit_size // 2)
        uninit_data += b'\xcc' * (uninit_size - len(uninit_data))
        
        poc += struct.pack('>I', len(uninit_data))  # Size field
        poc += uninit_data
        
        # Ensure exact target length
        if len(poc) < 2179:
            poc += b'\x00' * (2179 - len(poc))
        elif len(poc) > 2179:
            poc = poc[:2179]
        
        return poc
    
    def _generate_text_poc(self, hints):
        """Generate text PoC for formats like XML/JSON."""
        # Create text file with malformed attributes
        poc = '<?xml version="1.0"?>\n'
        poc += '<root>\n'
        poc += '  <item '
        
        # Add attribute that might fail conversion
        if 'conversion' in hints['keywords']:
            poc += 'size="' + 'A' * 500  # Non-numeric for numeric conversion
        
        # Add uninitialized-like content
        poc += ' value="'
        
        # Fill to target length
        current_len = len(poc)
        remaining = 2179 - current_len - 20  # Reserve for closing tags
        
        # Add content that looks uninitialized
        poc += '\x00' * (remaining // 2)
        poc += 'UNINIT' * ((remaining // 2) // 6)
        
        poc += '">\n'
        poc += '</item>\n'
        poc += '</root>'
        
        # Pad or truncate to exact length
        poc_bytes = poc.encode('utf-8', errors='ignore')
        if len(poc_bytes) < 2179:
            poc_bytes += b'\x00' * (2179 - len(poc_bytes))
        elif len(poc_bytes) > 2179:
            poc_bytes = poc_bytes[:2179]
        
        return poc_bytes
