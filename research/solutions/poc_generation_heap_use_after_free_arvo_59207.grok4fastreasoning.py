import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        parts = []
        current_pos = 0

        header = b'%PDF-1.5\n%\xe2\xe3\xef\xd3\n\n'
        parts.append(header)
        current_pos += len(header)

        obj_offsets = {}

        def add_obj(num: int, content: bytes):
            nonlocal current_pos
            obj_header = f'{num} 0 obj\n'.encode('ascii')
            parts.append(obj_header)
            current_pos += len(obj_header)
            parts.append(content)
            current_pos += len(content)
            parts.append(b'endobj\n')
            current_pos += 7
            obj_offsets[num] = obj_offsets.get(num, current_pos - len(obj_header) - len(content) - 7)

        # Inner content for object 5 (contents stream)
        inner_stream = b'BT /F1 12 Tf 100 700 Td (Hello World) Tj ET'
        inner_len_bytes = len(inner_stream)
        inner_dict = b'<< /Length ' + str(inner_len_bytes).encode('ascii') + b' >>\n'
        inner_content = inner_dict + b'stream\n' + inner_stream + b'\nendstream\n'

        # ObjStm data: index + inner content
        index_data = struct.pack('>I', 5) + struct.pack('>I', 8)
        objstm_data = index_data + inner_content

        # Object 1: Catalog
        catalog = b'<< /Type /Catalog /Pages 2 0 R >>\n'
        add_obj(1, catalog)

        # Object 2: Pages
        pages = b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n'
        add_obj(2, pages)

        # Object 3: Page
        page = b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 6 0 R >> >> >>\n'
        add_obj(3, page)

        # Object 6: Font
        font = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n'
        add_obj(6, font)

        # Object 4: ObjStm (stream)
        objstm_header = b'<< /Type /ObjStm /N 1 /First 8 /Length 20 0 R >>\nstream\n'
        objstm_content = objstm_header + objstm_data + b'endstream\n'
        add_obj(4, objstm_content)

        # Now build xref stream (object 7)
        xrefstm_off = current_pos
        obj_offsets[7] = xrefstm_off

        # Build xref entries
        xref_entries = [None] * 8
        xref_entries[0] = b'\x00' + struct.pack('>I', 0) + struct.pack('>H', 65535)
        for i in [1, 2, 3, 4, 6, 7]:
            off = obj_offsets[i]
            xref_entries[i] = b'\x01' + struct.pack('>I', off) + struct.pack('>H', 0)
        xref_entries[5] = b'\x02' + struct.pack('>I', 4) + struct.pack('>H', 0)
        xref_data = b''.join(xref_entries)

        # XRefStm dict and content
        xref_dict = b'<< /Type /XRef /Size 8 /W [1 4 2] /Index [0 8] >>\n'
        xref_header = xref_dict + b'stream\n'
        xref_content = xref_header + xref_data + b'\nendstream\n'
        add_obj(7, xref_content)

        # startxref and trailer
        startxref_pos = obj_offsets[7]
        parts.append(b'startxref\n')
        current_pos += 10
        parts.append(str(startxref_pos).encode('ascii') + b'\n')
        current_pos += len(str(startxref_pos)) + 1
        trailer = b'<< /Size 8 /Root 1 0 R >>\n%%EOF\n'
        parts.append(trailer)

        return b''.join(parts)