import struct


def _make_minimal_zip_with_long_name(name_len: int) -> bytes:
    name = b"A" * name_len

    crc32 = 0
    comp_size = 0
    uncomp_size = 0
    method = 0  # stored
    flags = 0
    mod_time = 0
    mod_date = 0
    ver_needed = 20
    ver_made = 20
    extra = b""
    comment = b""

    # Local file header
    local_sig = 0x04034B50
    local_hdr = struct.pack(
        "<IHHHHHIIIHH",
        local_sig,
        ver_needed,
        flags,
        method,
        mod_time,
        mod_date,
        crc32,
        comp_size,
        uncomp_size,
        len(name),
        len(extra),
    )
    local = local_hdr + name + extra  # + data (0 bytes)

    local_offset = 0
    central_sig = 0x02014B50
    central_hdr = struct.pack(
        "<IHHHHHHIIIHHHHHII",
        central_sig,
        ver_made,
        ver_needed,
        flags,
        method,
        mod_time,
        mod_date,
        crc32,
        comp_size,
        uncomp_size,
        len(name),
        len(extra),
        len(comment),
        0,  # disk number start
        0,  # internal file attributes
        0,  # external file attributes
        local_offset,
    )
    central = central_hdr + name + extra + comment

    central_offset = len(local)
    central_size = len(central)

    eocd_sig = 0x06054B50
    eocd = struct.pack(
        "<IHHHHIIH",
        eocd_sig,
        0,  # number of this disk
        0,  # disk where central directory starts
        1,  # number of central directory records on this disk
        1,  # total number of central directory records
        central_size,
        central_offset,
        0,  # comment length
    )

    return local + central + eocd


class Solution:
    def solve(self, src_path: str) -> bytes:
        return _make_minimal_zip_with_long_name(257)