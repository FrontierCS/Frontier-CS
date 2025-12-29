import zlib
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        best_deflate = None
        best_data = None

        # Prepare strategies to try
        strategies = []
        if hasattr(zlib, "Z_HUFFMAN_ONLY"):
            strategies.append(zlib.Z_HUFFMAN_ONLY)
        if hasattr(zlib, "Z_FILTERED"):
            strategies.append(zlib.Z_FILTERED)
        if hasattr(zlib, "Z_DEFAULT_STRATEGY"):
            strategies.append(zlib.Z_DEFAULT_STRATEGY)
        if not strategies:
            strategies = [0]

        # Try various small inputs and compression settings to get a dynamic Huffman block
        for size in range(1, 65):
            # Use a couple of patterns to encourage dynamic Huffman use
            patterns = [b"A" * size, bytes((i % 256 for i in range(size)))]
            for data in patterns:
                for strategy in strategies:
                    for level in (9, 6, 3, 1):
                        try:
                            co = zlib.compressobj(
                                level,
                                zlib.DEFLATED,
                                wbits=-15,  # raw deflate
                                memLevel=8,
                                strategy=strategy,
                            )
                        except TypeError:
                            # Older zlib: strategy may not be accepted
                            co = zlib.compressobj(
                                level,
                                zlib.DEFLATED,
                                wbits=-15,
                                memLevel=8,
                            )
                        d = co.compress(data) + co.flush()
                        if not d:
                            continue
                        # Check first block type: bits 1-2 of first byte (LSB first)
                        btype = (d[0] >> 1) & 0x3
                        if btype != 0b10:  # not dynamic Huffman
                            continue
                        if best_deflate is None or len(d) < len(best_deflate):
                            best_deflate = d
                            best_data = data

        # Fallback if, for some reason, no dynamic Huffman block was found
        if best_deflate is None:
            best_data = b"A" * 32
            co = zlib.compressobj(9, zlib.DEFLATED, wbits=-15)
            best_deflate = co.compress(best_data) + co.flush()

        # Build minimal gzip wrapper around the raw deflate stream
        crc = zlib.crc32(best_data) & 0xFFFFFFFF
        isize = len(best_data) & 0xFFFFFFFF

        # Gzip header: ID1 ID2 CM FLG MTIME(4) XFL OS
        header = b"\x1f\x8b\x08\x00" + b"\x00\x00\x00\x00" + b"\x00" + b"\x03"
        tail = struct.pack("<II", crc, isize)

        return header + best_deflate + tail